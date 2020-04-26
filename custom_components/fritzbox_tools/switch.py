"""Switches for AVM Fritz!Box functions"""
import logging
from typing import List  # noqa
from datetime import timedelta
import time
import xmltodict

from collections import Counter, defaultdict

from homeassistant.components.switch import SwitchDevice, ENTITY_ID_FORMAT
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import slugify

from . import DOMAIN, DATA_FRITZ_TOOLS_INSTANCE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)  # update of profile switch takes too long


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    _LOGGER.debug("Setting up switches")
    fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]

    def _create_deflection_switches():
        deflections_response = fritzbox_tools.connection.call_action("X_AVM-DE_OnTel:1", "GetNumberOfDeflections")
        _LOGGER.debug(deflections_response)
        _LOGGER.debug(fritzbox_tools.connection.services)
        if "X_AVM-DE_OnTel1" in fritzbox_tools.connection.services and deflections_response["NewNumberOfDeflections"] != 0:
            try:
                _LOGGER.debug("Setting up deflection switches")
                deflections = xmltodict.parse(
                    fritzbox_tools.connection.call_action("X_AVM-DE_OnTel:1", "GetDeflections")["NewDeflectionList"]
                )["List"]["Item"]
                if not isinstance(deflections, list):
                    deflections = [deflections]

                for dict_of_deflection in deflections:
                    hass.add_job(
                        async_add_entities,
                        [
                            FritzBoxDeflectionSwitch(
                                fritzbox_tools, dict_of_deflection
                            )
                        ],
                    )

            except Exception:
                _LOGGER.error(
                    f"Call Deflection switches could not be enabled.",
                    exc_info=True,
                )

    def _create_port_switches():
        if fritzbox_tools.ha_ip != "127.0.0.1":
            try:
                _LOGGER.debug("Setting up port forward switches")
                connection_type = fritzbox_tools.connection.call_action(
                    "Layer3Forwarding:1", "GetDefaultConnectionService"
                )["NewDefaultConnectionService"]
                connection_type = connection_type[2:].replace(".", ":")

                # Query port forwardings and setup a switch for each forward for the current device
                port_forwards_count: int = fritzbox_tools.connection.call_action(
                    connection_type, "GetPortMappingNumberOfEntries"
                )["NewPortMappingNumberOfEntries"]
                _LOGGER.debug('Number of port forwards response')
                _LOGGER.debug(port_forwards_count)
                for i in range(port_forwards_count):
                    portmap = fritzbox_tools.connection.call_action(
                        connection_type,
                        "GetGenericPortMappingEntry",
                        NewPortMappingIndex=i,
                    )
                    _LOGGER.debug("Specific port forward response")
                    _LOGGER.debug(portmap)

                    _LOGGER.debug(f"Port forwards of the following device are shown: {fritzbox_tools.ha_ip}")

                    # We can only handle port forwards of the given device
                    if portmap["NewInternalClient"] == fritzbox_tools.ha_ip:
                        hass.add_job(
                            async_add_entities,
                            [
                                FritzBoxPortSwitch(
                                    fritzbox_tools, portmap, i, connection_type
                                )
                            ],
                        )

            except Exception:
                _LOGGER.error(
                    f"Port switches could not be enabled. Check if your fritzbox is able to do port forwardings!",
                    exc_info=True,
                )

    def _create_profile_switches():
        if len(fritzbox_tools.device_list) > 0:
            _LOGGER.debug("Setting up profile switches")
            devices = fritzbox_tools.profile_switch.get_devices()

            # Identify duplicated host names and log an error message
            hostname_count = Counter([device["name"] for device in devices])
            duplicated_hostnames = [
                name for name, occurence in hostname_count.items() if occurence > 1
            ]
            if len(duplicated_hostnames) > 0:
                errs = ", ".join(duplicated_hostnames)
                _LOGGER.error(
                    f"You have multiple devices with the hostname {errs} in your network. "
                    "There will be no profile switches created for these."
                )

            # add device switches
            for device in devices:
                # Check for duplicated host names in the devices list.
                if device["name"] not in duplicated_hostnames:
                    if device["name"] in fritzbox_tools.device_list:
                        _LOGGER.debug(f"device to be added: {device}")
                        hass.add_job(
                            async_add_entities,
                            [FritzBoxProfileSwitch(fritzbox_tools, device)],
                        )

    def _create_wifi_switches():
        if "WLANConfiguration3" not in fritzbox_tools.connection.services:
            networks = {"1": "Wifi", "2": "Guest Wifi"}
        else:
            networks = {"1": "Wifi", "2": "Wifi (5GHz)", "3": "Guest Wifi"}

        for net in networks:
            hass.add_job(
                async_add_entities,
                [FritzBoxWifiSwitch(fritzbox_tools, net, networks[net])],
            )
    if fritzbox_tools.use_wifi:
        hass.async_add_executor_job(_create_wifi_switches)
    if fritzbox_tools.use_port:
        hass.async_add_executor_job(_create_port_switches)
    if fritzbox_tools.use_deflections:
        hass.async_add_executor_job(_create_deflection_switches)
    if fritzbox_tools.use_devices:
        hass.async_add_executor_job(_create_profile_switches)

    _LOGGER.debug(f"use_wifi: {fritzbox_tools.use_wifi}")
    _LOGGER.debug(f"use_devices: {fritzbox_tools.use_devices}")
    _LOGGER.debug(f"use_deflections: {fritzbox_tools.use_deflections}")
    _LOGGER.debug(f"use_port: {fritzbox_tools.use_port}")

    return True


class FritzBoxPortSwitch(SwitchDevice):
    """Defines a FRITZ!Box Tools PortForward switch."""

    icon = "mdi:lan"
    _update_grace_period = 5  # seconds

    def __init__(self, fritzbox_tools, port_mapping, idx, connection_type):
        self.fritzbox_tools = fritzbox_tools
        self.connection_type = connection_type
        self.port_mapping: dict = port_mapping  # dict in the format as it comes from fritzconnection. eg: {'NewRemoteHost': '0.0.0.0', 'NewExternalPort': 22, 'NewProtocol': 'TCP', 'NewInternalPort': 22, 'NewInternalClient': '192.168.178.31', 'NewEnabled': True, 'NewPortMappingDescription': 'Beast SSH ', 'NewLeaseDuration': 0}  # noqa

        description = port_mapping["NewPortMappingDescription"]
        self._name = f"Port forward {description}"
        id = f"fritzbox_portforward_{slugify(description)}"
        self.entity_id = ENTITY_ID_FORMAT.format(id)

        self._attributes = defaultdict(str)
        self._is_available = (
            True  # set to False if an error happend during toggling the switch
        )
        self._is_on = self.port_mapping["NewEnabled"] is True

        self._idx = idx  # needed for update routine
        self._last_toggle_timestamp = None
        super().__init__()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self.fritzbox_tools.unique_id}-{self.entity_id}"

    @property
    def device_info(self):
        return self.fritzbox_tools.device_info

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    @property
    def device_state_attributes(self) -> dict:
        return self._attributes

    async def _async_fetch_update(self):
        from fritzconnection.core.exceptions import FritzConnectionException

        try:
            self.port_mapping = await self.hass.async_add_executor_job(lambda: self.fritzbox_tools.connection.call_action(
                self.connection_type,
                "GetGenericPortMappingEntry",
                NewPortMappingIndex=self._idx,
            ))
            _LOGGER.debug(self.port_mapping)
            self._is_on = self.port_mapping["NewEnabled"] is True
            self._is_available = True

            self._attributes["internalIP"] = self.port_mapping["NewInternalClient"]
            self._attributes["internalPort"] = self.port_mapping["NewInternalPort"]
            self._attributes["externalPort"] = self.port_mapping["NewExternalPort"]
            self._attributes["protocol"] = self.port_mapping["NewProtocol"]
            self._attributes["description"] = self.port_mapping[
                "NewPortMappingDescription"
            ]
        except FritzConnectionException:
            _LOGGER.error(
                "Authorization Error: Please check the provided credentials and verify that you can log "
                "into the web interface."
            )
            self._is_available = False  # noqa
        except Exception:
            _LOGGER.error("Could not get state of Port forwarding", exc_info=True)
            self._is_available = False  # noqa

    async def async_update(self):
        if (
            self._last_toggle_timestamp is not None
            and time.time() < self._last_toggle_timestamp + self._update_grace_period
        ):
            # We skip update for 5 seconds after toggling the switch
            # This is because the router needs some time to change the guest wifi state
            _LOGGER.debug(
                "Not updating switch state, because last toggle happend < 5 seconds ago"
            )
        else:
            _LOGGER.debug("Updating port switch state...")
            # Update state from device
            await self._async_fetch_update()

    async def async_turn_on(self, **kwargs) -> None:
        success: bool = await self._async_handle_port_switch_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error(
                "An error occurred while turning on fritzbox_tools port forwarding wifi switch."
            )

    async def async_turn_off(self, **kwargs) -> None:
        success: bool = await self._async_handle_port_switch_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error(
                "An error occurred while turning off fritzbox_tools port forwarding switch."
            )

    async def _async_handle_port_switch_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        from fritzconnection.core.exceptions import FritzSecurityError, FritzConnectionException

        self.port_mapping["NewEnabled"] = "1" if turn_on else "0"
        try:
            self.hass.async_add_executor_job(lambda: self.fritzbox_tools.connection.call_action(
                self.connection_type, "AddPortMapping", **self.port_mapping
            ))
        except FritzSecurityError:
            _LOGGER.error(
                "Authorization Error: Please check the provided credentials and verify that you can log into "
                "the web interface.",
                exc_info=True,
            )
        except FritzConnectionException:
            _LOGGER.error(
                "Home Assistant cannot call the wished service on the FRITZ!Box.",
                exc_info=True,
            )
            return False
        else:
            return True


class FritzBoxDeflectionSwitch(SwitchDevice):
    """Defines a FRITZ!Box Tools PortForward switch."""

    icon = "mdi:phone-forward"
    _update_grace_period = 30  # seconds

    def __init__(self, fritzbox_tools, dict_of_deflection):
        self.fritzbox_tools = fritzbox_tools
        self.dict_of_deflection = dict_of_deflection
        self.id = int(self.dict_of_deflection["DeflectionId"])
        self._name = f"Deflection {self.id}"
        id = f"fritzbox_deflection_{self.id}"
        self.entity_id = ENTITY_ID_FORMAT.format(id)

        self._attributes = defaultdict(str)
        self._is_available = (
            True  # set to False if an error happend during toggling the switch
        )
        self._is_on = self.dict_of_deflection["Enable"] is True

        self._last_toggle_timestamp = None
        super().__init__()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self.fritzbox_tools.unique_id}-{self.entity_id}"

    @property
    def device_info(self):
        return self.fritzbox_tools.device_info

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    @property
    def device_state_attributes(self) -> dict:
        return self._attributes

    async def _async_fetch_update(self):
        from fritzconnection.core.exceptions import FritzConnectionException

        try:
            resp = await self.hass.async_add_executor_job(
                lambda: self.fritzbox_tools.connection.call_action("X_AVM-DE_OnTel:1", "GetDeflections")
            )
            self.dict_of_deflection = xmltodict.parse(
                resp["NewDeflectionList"]
            )["List"]["Item"]
            if isinstance(self.dict_of_deflection, list):
                self.dict_of_deflection = self.dict_of_deflection[self.id]

            _LOGGER.debug("GetDeflections:")
            _LOGGER.debug(self.dict_of_deflection)

            self._is_on = self.dict_of_deflection["Enable"] == '1'
            self._is_available = True

            self._attributes["Type"] = self.dict_of_deflection["Type"]
            self._attributes["Number"] =  self.dict_of_deflection["Number"]
            self._attributes["DeflectionToNumber"] =  self.dict_of_deflection["DeflectionToNumber"]
            self._attributes["Mode"] =  self.dict_of_deflection["Mode"]
            self._attributes["Outgoing"] =  self.dict_of_deflection["Outgoing"]
            self._attributes["PhonebookID"] =  self.dict_of_deflection["PhonebookID"]

        except FritzConnectionException:
            _LOGGER.error(
                "Authorization Error: Please check the provided credentials and verify that you can log "
                "into the web interface."
            )
            self._is_available = False  # noqa
        except Exception:
            _LOGGER.error("Could not get state of Port forwarding", exc_info=True)
            self._is_available = False  # noqa

    async def async_update(self):
        if (
            self._last_toggle_timestamp is not None
            and time.time() < self._last_toggle_timestamp + self._update_grace_period
        ):
            # We skip update for 5 seconds after toggling the switch
            # This is because the router needs some time to change the guest wifi state
            _LOGGER.debug(
                "Not updating switch state, because last toggle happend < 5 seconds ago"
            )
        else:
            _LOGGER.debug("Updating call deflection switch state...")
            # Update state from device
            await self._async_fetch_update()

    async def async_turn_on(self, **kwargs) -> None:
        success: bool = await self._async_handle_deflection_switch_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error(
                "An error occurred while turning on fritzbox_tools Deflection switch."
            )

    async def async_turn_off(self, **kwargs) -> None:
        success: bool = await self._async_handle_deflection_switch_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error(
                "An error occurred while turning off fritzbox_tools Deflection switch."
            )

    async def _async_handle_deflection_switch_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        from fritzconnection.core.exceptions import FritzSecurityError, FritzConnectionException

        new_state = '1' if turn_on else '0'
        try:
            self.hass.async_add_executor_job(lambda: self.fritzbox_tools.connection.call_action(
                "X_AVM-DE_OnTel:1","SetDeflectionEnable", NewDeflectionId=self.id, NewEnable=new_state
            ))
        except FritzSecurityError:
            _LOGGER.error(
                "Authorization Error: Please check the provided credentials and verify that you can log into "
                "the web interface.",
                exc_info=True,
            )
        except FritzConnectionException:
            _LOGGER.error(
                "Home Assistant cannot call the wished service on the FRITZ!Box.",
                exc_info=True,
            )
            return False
        else:
            return True


class FritzBoxProfileSwitch(SwitchDevice):
    """Defines a FRITZ!Box Tools DeviceProfile switch."""

    # Note: Update routine is very slow. SCAN_INTERVAL should be set to higher values!

    icon = "mdi:lan"  # TODO: search for a better one
    _update_grace_period = 30  # seconds

    def __init__(self, fritzbox_tools, device):
        self.fritzbox_tools = fritzbox_tools
        self.device = device
        self.profiles = self.fritzbox_tools.profile_switch.get_profiles()
        for i in range(len(self.profiles)):
            if self.profiles[i]["name"] == self.fritzbox_tools.profile_off:
                self.id_off = self.profiles[i]["id"]
            elif self.profiles[i]["name"] == self.fritzbox_tools.profile_on:
                self.id_on = self.profiles[i]["id"]
        try:
            self.id_off, self.id_on
        except AttributeError:
            _LOGGER.error(
                "profile_on or profile_off does not match any profiles in your fritzbox"
            )

        name = self.device["name"]
        self._name = f"Device Profile {name}"
        id = f"fritzbox_profile_{name}"
        self.entity_id = ENTITY_ID_FORMAT.format(slugify(id))

        if self.device["profile"] == self.id_off:
            self._is_on = False
        else:
            self._is_on = True  # TODO: Decide on default behaviour

        self._last_toggle_timestamp = None
        self._is_available = (
            True  # set to False if an error happend during toggling the switch
        )
        if (
            self.id_on is None or self.id_off is None
        ):  # that's the case if wrong setting in config.
            self._is_available = False
            _LOGGER.error(
                "The profile you tried to set does not exist in the fritzbox. "
                "Please check profile_on and profile_off in your config for errors"
            )

        super().__init__()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self.fritzbox_tools.unique_id}-{self.entity_id}"

    @property
    def device_info(self):
        return self.fritzbox_tools.device_info

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    async def _async_fetch_update(self):
        await self.fritzbox_tools.async_update_profiles(self.hass)
        try:
            devices = self.fritzbox_tools.profile_switch.get_devices()
            for device in devices:
                self.device = (
                    device if device["name"] == self.device["name"] else self.device
                )
            self.profiles = self.fritzbox_tools.profile_switch.get_profiles()
            if self.device["profile"] == self.id_off:
                self._is_on = False
            else:
                self._is_on = True  # TODO: Decide on default behaviour
            self._is_available = True
        except Exception:
            _LOGGER.error(
                f"Could not get state of profile switch", exc_info=True
            )  # TODO: get detailed error
            self._is_available = False

    async def async_update(self):
        if (
            self._last_toggle_timestamp is not None
            and time.time() < self._last_toggle_timestamp + self._update_grace_period
        ):
            # We skip update for 5 seconds after toggling the switch
            # This is because the router needs some time to change the guest wifi state
            _LOGGER.debug(
                "Not updating switch state, because last toggle happend < {} seconds ago".format(
                    self._update_grace_period
                )
            )
        else:
            await self._async_fetch_update()

    async def async_turn_on(self, **kwargs) -> None:
        success: bool = await self._async_handle_profile_switch_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error(
                "An error occurred while turning on fritzbox_tools Guest wifi switch."
            )

    async def async_turn_off(self, **kwargs) -> None:
        success: bool = await self._async_handle_profile_switch_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error(
                "An error occurred while turning off fritzbox_tools Guest wifi switch."
            )

    async def _async_handle_profile_switch_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        if turn_on:
            state = [[self.device["id1"], self.id_on]]
        else:
            state = [[self.device["id1"], self.id_off]]
        try:
            await self.hass.async_add_executor_job(lambda: self.fritzbox_tools.profile_switch.set_profiles(state))
        except Exception:
            _LOGGER.error(
                f"Home Assistant cannot call the wished service on the FRITZ!Box.",
                exc_info=True,
            )
            return False
        else:
            return True


class FritzBoxWifiSwitch(SwitchDevice):
    """Defines a FRITZ!Box Tools Wifi switch."""

    icon = "mdi:wifi"
    _update_grace_period = 5  # seconds

    def __init__(self, fritzbox_tools, network_num, network_name):
        self._fritzbox_tools = fritzbox_tools
        self._network_num = network_num
        id = network_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
        self.entity_id = ENTITY_ID_FORMAT.format(f"fritzbox_{id}")
        self._name = f"FRITZ!Box {network_name}"
        self._is_on = False
        self._last_toggle_timestamp = None
        self._is_available = (
            True  # set to False if an error happend during toggling the switch
        )
        super().__init__()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self._fritzbox_tools.unique_id}-{self.entity_id}"

    @property
    def device_info(self):
        return self._fritzbox_tools.device_info

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    async def _async_fetch_update(self):
        from fritzconnection.core.exceptions import FritzConnectionException

        try:
            wifi_info = await self.hass.async_add_executor_job(lambda: self._fritzbox_tools.connection.call_action(
                f"WLANConfiguration:{self._network_num}", "GetInfo"
            ))
            _LOGGER.debug("Guest WiFi GetInfo:")
            _LOGGER.debug(wifi_info)
            self._is_on = True if wifi_info["NewStatus"] == "Up" else False
            self._is_available = True
        except FritzConnectionException:
            _LOGGER.error(
                "Authorization Error: Please check the provided credentials and verify that you can log "
                "into the web interface.",
                exc_info=True,
            )
            self._is_available = False
        except Exception:
            _LOGGER.error(f"Could not get {self.name} state", exc_info=True)
            self._is_available = False

    async def async_update(self):
        if (
            self._last_toggle_timestamp is not None
            and time.time() < self._last_toggle_timestamp + self._update_grace_period
        ):
            # We skip update for 5 seconds after toggling the switch
            # This is because the router needs some time to change the wifi state
            _LOGGER.debug(
                "Not updating switch state, because last toggle happend < 5 seconds ago"
            )
        else:
            _LOGGER.debug(f"Updating {self.name} switch state...")
            # Update state from device
            await self._async_fetch_update()

    async def async_turn_on(self, **kwargs) -> None:
        success: bool = await self._async_handle_wifi_turn_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error(
                f"An error occurred while turning on fritzbox_tools {self.name} switch."
            )

    async def async_turn_off(self, **kwargs) -> None:
        success: bool = await self._async_handle_wifi_turn_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error(
                f"An error occurred while turning off fritzbox_tools {self.name} switch."
            )

    async def _async_handle_wifi_turn_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        from fritzconnection.core.exceptions import FritzSecurityError, FritzConnectionException

        try:
            self.hass.async_add_executor_job(lambda: self._fritzbox_tools.connection.call_action(
                f"WLANConfiguration{self._network_num}", "SetEnable", NewEnable="1" if turn_on else "0"
            ))
        except FritzSecurityError:
            _LOGGER.error(
                "Authorization Error: Please check the provided credentials and verify that you can log into "
                "the web interface.",
                exc_info=True,
            )
        except FritzConnectionException:
            _LOGGER.error(
                "Home Assistant cannot call the wished service on the FRITZ!Box.",
                exc_info=True,
            )
            return False
        else:
            return True
