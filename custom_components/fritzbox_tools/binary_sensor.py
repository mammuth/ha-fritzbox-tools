"""AVM Fritz!Box connectivitiy sensor"""
import logging
from collections import defaultdict
import datetime

try:
    from homeassistant.components.binary_sensor import ENTITY_ID_FORMAT, BinarySensorEntity
except ImportError:
    from homeassistant.components.binary_sensor import ENTITY_ID_FORMAT, BinarySensorDevice as BinarySensorEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from . import DATA_FRITZ_TOOLS_INSTANCE, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = datetime.timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    _LOGGER.debug("Setting up sensors")
    fritzbox_tools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE][entry.entry_id]

    if "WANIPConn1" in fritzbox_tools.connection.services:
        """ We do not support repeaters at the moment """
        async_add_entities([FritzBoxConnectivitySensor(fritzbox_tools)], True)

    return True


class FritzBoxConnectivitySensor(BinarySensorEntity):
    name = "FRITZ!Box Connectivity"
    icon = "mdi:router-wireless"
    device_class = "connectivity"

    def __init__(self, fritzbox_tools):
        self.fritzbox_tools = fritzbox_tools
        self.entity_id = ENTITY_ID_FORMAT.format(f"fritzbox_{self.fritzbox_tools.fritzbox_model}_connectivity")
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
            if "WANCommonInterfaceConfig1" in self.fritzbox_tools.connection.services:
                connection = lambda: self.fritzbox_tools.connection.call_action("WANCommonInterfaceConfig1", "GetCommonLinkProperties")["NewPhysicalLinkStatus"]
                is_up = await self.hass.async_add_executor_job(connection)
                self._is_on = is_up == "Up"
            else:
                self._is_on = self.hass.async_add_executor_job(self.fritzbox_tools.fritzstatus.is_connected)

            self._is_available = True

            status = self.fritzbox_tools.fritzstatus
            uptime_seconds = await self.hass.async_add_executor_job(lambda: getattr(status, "uptime"))
            last_reconnect = datetime.datetime.now() - datetime.timedelta(seconds=uptime_seconds)
            self._attributes["last_reconnect"] = last_reconnect.replace(microsecond=0).isoformat()

            for attr in [
                "modelname",
                "external_ip",
                "external_ipv6",
            ]:    
                self._attributes[attr] = await self.hass.async_add_executor_job(lambda: getattr(status, attr))
                    
        except Exception:
            _LOGGER.error("Error getting the state from the FRITZ!Box", exc_info=True)
            self._is_available = False

    async def async_update(self) -> None:
        _LOGGER.debug("Updating Connectivity sensor...")
        await self._async_fetch_update()
