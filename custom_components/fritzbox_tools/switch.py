import logging
from typing import Optional
from datetime import timedelta
import time

from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA

from . import DOMAIN, DATA_FRITZ_TOOLS_INSTANCE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)


def setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug('Setting up switches')
    fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]
    # add_entities([FritzBoxGuestWifiSwitch(fritzbox_tools)])
    add_entities([FritzBoxGuestWifiSwitch(fritzbox_tools)], True)
    return True


class FritzBoxGuestWifiSwitch(SwitchDevice):
    """Defines a fritzbox_tools Home switch."""

    name = 'FRITZ!Box Guest Wifi'
    icon = 'mdi:wifi'
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
        success: bool = self.fritzbox_tools.handle_guestwifi_turn_on_off(turn_on=True)
        if success is True:
            self._is_on = True
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = False
            _LOGGER.error("An error occurred while turning on fritzbox_tools Guest wifi switch.")

    def turn_off(self, **kwargs) -> None:
        success: bool = self.fritzbox_tools.handle_guestwifi_turn_on_off(turn_on=False)
        if success is True:
            self._is_on = False
            self._last_toggle_timestamp = time.time()
        else:
            self._is_on = True
            _LOGGER.error("An error occurred while turning off fritzbox_tools Guest wifi switch.")
