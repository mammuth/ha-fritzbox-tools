"""AVM Fritz!Box connectivitiy sensor"""
import logging
from collections import defaultdict
from datetime import timedelta

from homeassistant.components.binary_sensor import ENTITY_ID_FORMAT, BinarySensorDevice
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from . import DATA_FRITZ_TOOLS_INSTANCE, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    _LOGGER.debug("Setting up sensors")
    fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]

    async_add_entities([FritzBoxConnectivitySensor(fritzbox_tools)], True)
    return True


class FritzBoxConnectivitySensor(BinarySensorDevice):
    name = "FRITZ!Box Connectivity"
    entity_id = ENTITY_ID_FORMAT.format("fritzbox_connectivity")
    icon = "mdi:router-wireless"
    device_class = "connectivity"

    def __init__(self, fritzbox_tools):
        self.fritzbox_tools = fritzbox_tools
        self._is_on = True  # We assume the fritzbox to be online initially
        self._is_available = (
            True  # set to False if an error happend during toggling the switch
        )
        self._attributes = defaultdict(str)
        super().__init__()

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def unique_id(self):
        return f"{self.fritzbox_tools.unique_id}-{self.entity_id}"

    @property
    def device_info(self):
        return self.fritzbox_tools.device_info

    @property
    def available(self) -> bool:
        return self._is_available

    @property
    def device_state_attributes(self) -> dict:
        return self._attributes

    async def _async_fetch_update(self):
        self._is_on = True
        try:
            status = self.fritzbox_tools.fritzstatus
            self._is_on = status.is_connected
            self._is_available = True
            for attr in [
                "modelname",
                "external_ip",
                "external_ipv6",
                "uptime",
                "str_uptime",
            ]:
                self._attributes[attr] = getattr(status, attr)
        except Exception:
            _LOGGER.error("Error getting the state from the FRITZ!Box", exc_info=True)
            self._is_available = False

    async def async_update(self) -> None:
        _LOGGER.debug("Updating Connectivity sensor...")
        await self._async_fetch_update()
