import logging
import time
from datetime import timedelta

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


# async def async_setup_platform(hass, config, add_entities, discovery_info=None):
#     """Set up the sensor platform."""
#     _LOGGER.debug('Setting up switches')
#     fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]
#     async_add_entities([FritzBoxGuestWifiSwitch(fritzbox_tools)])
#     return True


class FritzBoxGuestWifiSwitch(SwitchDevice):
    """Defines a fritzbox_tools Home switch."""

    name = 'FRITZ!Box Guest Wifi'
    icon = 'mdi:wifi'
    def __init__(self, fritzbox_tools):
        self.fritzbox_tools = fritzbox_tools
        self._is_on = False
        self._available = True  # set to False if an error happend during toggling the switch
        self._update_timestamp = time.time() - 60 
        super().__init__()

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    def update(self):
        _LOGGER.debug('Updating guest wifi switch state...')
        from fritzconnection.fritzconnection import AuthorizationError
        try:
            if time.time() > (self._update_timestamp + 60):
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
        result: bool = self.fritzbox_tools.handle_guestwifi_turn_on_off(turn_on=True)
        self._update_timestamp = time.time()
        if result is True:
            self._is_on = True
        else:
            _LOGGER.error("An error occurred while turning on fritzbox_tools Guest wifi switch.")

    def turn_off(self, **kwargs) -> None:
        result: bool = self.fritzbox_tools.handle_guestwifi_turn_on_off(turn_on=False)
        self._update_timestamp = time.time()
        if result is True:
            self._is_on = False
        else:
            _LOGGER.error("An error occurred while turning off fritzbox_tools Guest wifi switch.")
