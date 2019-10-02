import logging
from typing import Optional, List
from datetime import timedelta
import time

from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA

from . import DOMAIN, DATA_FRITZ_TOOLS_INSTANCE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30) # update of profile switch takes too long


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

    profile_switches: List[FritzBoxProfileSwitch] = []
    if fritzbox_tools.profile_on is not None:
        profile_available = True
        _LOGGER.debug('Setting up profile switches')
        devices = fritzbox_tools.profile_switch.get_devices()
        for i in range(len(devices)):
            for j in range(len(devices)): # TODO: a solution without two loops would be faster (python is really bad with nested loops)
                if devices[i]["name"] == devices[j]["name"] and i!=j:
                    _LOGGER.error('You have two devices in your network with the same hostname, this might break the profile switches. Change this and restart HomeAssistant.')
                    profile_available = False
                    break
            profile_switches.append(FritzBoxProfileSwitch(fritzbox_tools, devices[i]))
        if not profile_available: profile_switches = []


    add_entities([FritzBoxGuestWifiSwitch(fritzbox_tools)] + port_switches + profile_switches, True)
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
            ip=self.fritzbox_tools.ha_ip,
            port=port_mapping["NewExternalPort"],
            protocol=port_mapping["NewProtocol"]
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

class FritzBoxProfileSwitch(SwitchDevice):
    """Defines a fritzbox_tools DeviceProfile switch."""
    # Note: Update routine is very slow. SCAN_INTERVAL should be set to higher values!

    icon = 'mdi:lan' # TODO: search for a better one
    _update_grace_period = 30  # seconds

    def __init__(self, fritzbox_tools, device):
        self.fritzbox_tools = fritzbox_tools
        self.device = device
        self.profiles = self.fritzbox_tools.profile_switch.get_profiles()
        for i in range(len(self.profiles)):
            if self.profiles[i]['name'] == self.fritzbox_tools.profile_off:
                self.id_off = self.profiles[i]['id']
            elif self.profiles[i]['name'] == self.fritzbox_tools.profile_on:
                self.id_on = self.profiles[i]['id']
        # TODO: check if id_on has been set

        self._name = "FRITZ!Box Device Profile Switch for {}".format(self.device["name"])
        self._unique_id = "profile_{}".format(self.device["name"])

        if self.device["profile"] == self.id_off:
            self._is_on = False
        else: self._is_on = True # TODO: Decide on default behaviour

        self._last_toggle_timestamp = None
        self._available = True  # set to False if an error happend during toggling the switch
        if self.id_on is None or self.id_off is None: # thats the case if wrong setting in config.
            self._available = False
            _LOGGER.error('The profile you tried to set does not exist in the fritzbox. Please check profile_on and profile_off in your config for errors')

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
            _LOGGER.debug('Not updating switch state, because last toggle happend < '+str(self._update_grace_period)+' seconds ago')
        else:
            _LOGGER.debug('Updating profile switch state...')
            # Update state from device
            self.fritzbox_tools.update_profiles()
            try:
                devices = self.fritzbox_tools.profile_switch.get_devices()
                for device in devices:
                    self.device = device if device["name"] == self.device["name"] else self.device
                self.profiles =  self.fritzbox_tools.profile_switch.get_profiles()
                if self.device["profile"] == self.id_off:
                    self._is_on = False
                else: self._is_on = True # TODO: Decide on default behaviour
                self._is_available = True
            except:
                _LOGGER.error('Could not get state of profile switch') # TODO: get detailed error
                self._is_available = False

    def turn_on(self, **kwargs) -> None:
        success: bool = self._handle_profile_switch_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error("An error occurred while turning on fritzbox_tools Guest wifi switch.")

    def turn_off(self, **kwargs) -> None:
        success: bool = self._handle_profile_switch_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error("An error occurred while turning off fritzbox_tools Guest wifi switch.")

    def _handle_profile_switch_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        if turn_on:
            state = [[self.device['id1'], self.id_on]]
        else:
            state = [[self.device['id1'], self.id_off]]
        try:
            self.fritzbox_tools.profile_switch.set_profiles(state)
        except:
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
