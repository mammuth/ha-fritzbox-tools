import logging
from datetime import timedelta
from collections import defaultdict

from homeassistant.components.binary_sensor import BinarySensorDevice

from . import DOMAIN, DATA_FRITZ_TOOLS_INSTANCE

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


def setup_platform(hass, config, add_entities, discovery_info=None):
    _LOGGER.debug('Setting up sensors')
    fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]

    add_entities([FritzBoxConnectivitySensor(fritzbox_tools)], True)
    return True


class FritzBoxConnectivitySensor(BinarySensorDevice):
    name = 'FRITZ!Box Connectivity'
    icon = 'mdi:router-wireless'
    device_class = 'connectivity'

    def __init__(self, fritzbox_tools):
        self.fritzbox_tools = fritzbox_tools
        self._is_on = True  # We assume the fritzbox to be online initially
        self._is_available = True  # set to False if an error happend during toggling the switch
        self._attributes = defaultdict(str)
        super().__init__()

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def available(self) -> bool:
        return self._is_available

    @property
    def device_state_attributes(self) -> dict:
        return self._attributes

    def update(self) -> None:
        _LOGGER.debug('Updating Connectivity sensor...')
        self._is_on = True
        try:
            status = self.fritzbox_tools.fritzstatus
            self._is_on = status.is_connected
            self._is_available = True
            for attr in ['modelname', 'external_ip', 'external_ipv6', 'uptime', 'str_uptime']:
                self._attributes[attr] = getattr(status, attr)
        except Exception:
            _LOGGER.error('Error getting the state from the FRITZ!Box', exc_info=True)
            self._is_available = False
    