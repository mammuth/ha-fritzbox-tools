import logging
from typing import Optional, List
from datetime import timedelta
import time

from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA

from . import DOMAIN, DATA_FRITZ_TOOLS_INSTANCE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)


def setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug('Setting up switches')
    fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]

    port_switches: List[FritzBoxPortSwitch] = []
    if fritzbox_tools.ha_ip is not None:
        _LOGGER.debug('Setting up port forward switches')
        # Query port forwardings and setup a switch for each forward for the current deivce
        port_forwards_count: int = fritzbox_tools.connection.call_action('WANIPConnection:1', 'GetPortMappingNumberOfEntries')["NewPortMappingNumberOfEntries"]
        for i in range(port_forwards_count):
            portmap = fritzbox_tools.connection.call_action("WANIPConnection:1", "GetGenericPortMappingEntry", NewPortMappingIndex=i)
            # We can only handle port forwards of the given device
            if portmap["NewInternalClient"] == fritzbox_tools.ha_ip:
                port_switches.append(
                    FritzBoxPortSwitch(fritzbox_tools, portmap, i)
                )

    add_entities([FritzBoxGuestWifiSwitch(fritzbox_tools)] + port_switches, True)
    return True


class FritzBoxPortSwitch(SwitchDevice):
    """Defines a fritzbox_tools PortForward switch."""

    icon = 'mdi:lan'
    _update_grace_period = 5  # seconds

    def __init__(self, fritzbox_tools, port_mapping, idx):
        self.fritzbox_tools = fritzbox_tools
        self.port_mapping: dict = port_mapping  # dict in the format as it comes from fritzconnection. eg: {'NewRemoteHost': '0.0.0.0', 'NewExternalPort': 22, 'NewProtocol': 'TCP', 'NewInternalPort': 22, 'NewInternalClient': '192.168.178.31', 'NewEnabled': '0', 'NewPortMappingDescription': 'Beast SSH ', 'NewLeaseDuration': 0}

        self._name = "Port forward {}".format(port_mapping["NewPortMappingDescription"])
        self._unique_id = "fritzbox_portforward_{ip}_{port}_{protocol}".format(
            self.fritzbox_tools.ha_ip,
            port_mapping["NewExternalPort"],
            port_mapping["NewProtocol"]
        )
        self._idx = idx  # needed for update routine

        self._is_on = True if self.port_mapping["NewEnabled"] == "1" else False
        self._last_toggle_timestamp = None
        self._available = True  # set to False if an error happend during toggling the switch
        super().__init__()

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    def update(self):
        if self._last_toggle_timestamp is not None \
            and time.time() < self._last_toggle_timestamp + self._update_grace_period:
            # We skip update for 5 seconds after toggling the switch
            # This is because the router needs some time to change the guest wifi state
            _LOGGER.debug('Not updating switch state, because last toggle happend < 5 seconds ago')
        else:
            _LOGGER.debug('Updating port switch state...')
            # Update state from device
            from fritzconnection.fritzconnection import AuthorizationError
            try:
                self.port_mapping = self.fritzbox_tools.connection.call_action("WANIPConnection:1", "GetGenericPortMappingEntry",NewPortMappingIndex=self._idx)
                self._is_on = True if self.port_mapping["NewEnabled"] == "1" else False
                self._is_available = True
            except AuthorizationError:
                _LOGGER.error('Authorization Error: Please check the provided credentials and verify that you can log into the web interface.')
                self._is_available = False
            except Exception:
                _LOGGER.error('Could not get state of Port forwarding', exc_info=True)
                self._is_available = False

    def turn_on(self, **kwargs) -> None:
        success: bool = self._handle_port_switch_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error("An error occurred while turning on fritzbox_tools Guest wifi switch.")

    def turn_off(self, **kwargs) -> None:
        success: bool = self._handle_port_switch_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error("An error occurred while turning off fritzbox_tools Guest wifi switch.")

    def _handle_port_switch_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        from fritzconnection.fritzconnection import ServiceError, ActionError, AuthorizationError
        new_state = '1' if turn_on else '0'
        self.port_mapping["NewEnabled"] = new_state
        try:
            self.fritzbox_tools.connection.call_action("WANIPConnection:1","AddPortMapping",**self.port_mapping)
        except AuthorizationError:
            _LOGGER.error('Authorization Error: Please check the provided credentials and verify that you can log into the web interface.', exc_info=True)
        except (ServiceError, ActionError):
            _LOGGER.error('Home Assistant cannot call the wished service on the FRITZ!Box.', exc_info=True)
            return False
        else:
            return True

class FritzBoxGuestWifiSwitch(SwitchDevice):
    """Defines a fritzbox_tools Home switch."""

    name = 'FRITZ!Box Guest Wifi'
    icon = 'mdi:wifi'
    unique_id = 'fritzbox_guestwifi'
    _update_grace_period = 5  # seconds


    def __init__(self, fritzbox_tools):
        self.fritzbox_tools = fritzbox_tools
        self._is_on = False
        self._last_toggle_timestamp = None
        self._available = True  # set to False if an error happend during toggling the switch
        super().__init__()

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    def update(self):
        if self._last_toggle_timestamp is not None \
            and time.time() < self._last_toggle_timestamp + self._update_grace_period:
            # We skip update for 5 seconds after toggling the switch
            # This is because the router needs some time to change the guest wifi state
            _LOGGER.debug('Not updating switch state, because last toggle happend < 5 seconds ago')
        else:
            _LOGGER.debug('Updating guest wifi switch state...')
            # Update state from device
            from fritzconnection.fritzconnection import AuthorizationError
            try:
                status = self.fritzbox_tools.connection.call_action('WLANConfiguration:3', 'GetInfo')["NewStatus"]
                self._is_on = True if status == "Up" else False
                self._is_available = True
            except AuthorizationError:
                _LOGGER.error('Authorization Error: Please check the provided credentials and verify that you can log into the web interface.')
                self._is_available = False
            except Exception:
                _LOGGER.error('Could not get Guest Wifi state', exc_info=True)
                self._is_available = False

    def turn_on(self, **kwargs) -> None:
        success: bool = self._handle_guestwifi_turn_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error("An error occurred while turning on fritzbox_tools Guest wifi switch.")

    def turn_off(self, **kwargs) -> None:
        success: bool = self._handle_guestwifi_turn_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error("An error occurred while turning off fritzbox_tools Guest wifi switch.")

    def _handle_guestwifi_turn_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        from fritzconnection.fritzconnection import ServiceError, ActionError, AuthorizationError
        new_state = '1' if turn_on else '0'
        try:
            self.fritzbox_tools.connection.call_action('WLANConfiguration:3', 'SetEnable', NewEnable=new_state)
        except AuthorizationError:
            _LOGGER.error('Authorization Error: Please check the provided credentials and verify that you can log into the web interface.', exc_info=True)
        except (ServiceError, ActionError):
            _LOGGER.error('Home Assistant cannot call the wished service on the FRITZ!Box.', exc_info=True)
            return False
        else:
            return True
