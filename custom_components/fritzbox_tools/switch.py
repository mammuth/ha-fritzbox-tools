import logging

from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA

from . import DOMAIN, DATA_FRITZ_TOOLS_INSTANCE

_LOGGER = logging.getLogger(__name__)



def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
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

    def __init__(self, fritzbox_tools):
        self.fritzbox_tools = fritzbox_tools
        self._is_on = False
        self._available = True  # set to False if an error happend during toggling the switch
        super().__init__()

    @property
    def name(self) -> str:
        return 'FRITZ!Box Guest Wifi'

    @property
    def icon(self) -> str:
        return 'mdi:wifi'

    @property
    def assumed_state(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self._is_on

    def turn_on(self, **kwargs) -> None:
        result: bool = self.fritzbox_tools._handle_guestwifi_turn_on_off(turn_on=True)
        if result is True:
            self._is_on = True
            self._available = True
        else:
            _LOGGER.error("An error occurred while turning on fritzbox_tools Guest wifi switch.")
            self._available = False

    def turn_off(self, **kwargs) -> None:
        result: bool = self.fritzbox_tools._handle_guestwifi_turn_on_off(turn_on=False)
        if result is True:
            self._is_on = False
            self._available = True
        else:
            _LOGGER.error("An error occurred while turning off fritzbox_tools Guest wifi switch.")
            self._available = False
