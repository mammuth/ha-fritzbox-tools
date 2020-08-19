"""Support for AVM Fritz!Box functions"""
import asyncio
import logging
import time

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICES,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import get_local_ip

from .const import (
    CONF_PROFILE_OFF,
    CONF_PROFILE_ON,
    DEFAULT_DEVICES,
    DEFAULT_HOST,
    DEFAULT_USERNAME,
    DEFAULT_PORT,
    DEFAULT_PROFILE_OFF,
    DEFAULT_PROFILE_ON,
    DOMAIN,
    SERVICE_RECONNECT,
    SERVICE_REBOOT,
    SUPPORTED_DOMAINS,
    CONF_USE_WIFI,
    CONF_USE_DEVICES,
    CONF_USE_DEFLECTIONS,
    CONF_USE_PORT,
    DEFAULT_USE_WIFI,
    DEFAULT_USE_DEVICES,
    DEFAULT_USE_DEFLECTIONS,
    DEFAULT_USE_PORT,
)

REQUIREMENTS = ["fritzconnection==1.2.0", "fritz-switch-profiles==1.0.0", "xmltodict==0.12.0"]

DATA_FRITZ_TOOLS_INSTANCE = "fritzbox_tools_instance"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT): cv.port,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_DEVICES): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_PROFILE_ON): cv.string,
                vol.Optional(CONF_PROFILE_OFF): cv.string,
                vol.Optional(CONF_USE_DEVICES): cv.string,
                vol.Optional(CONF_USE_PORT): cv.string,
                vol.Optional(CONF_USE_WIFI): cv.string,
                vol.Optional(CONF_USE_DEFLECTIONS): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Setup FRITZ!Box Tools component"""
    if not hass.config_entries.async_entries(DOMAIN) and DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=config[DOMAIN],
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Setup fritzboxtools from config entry"""
    _LOGGER.debug("Setting up FRITZ!Box Tools component")
    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    profile_off = entry.data.get(CONF_PROFILE_OFF, DEFAULT_PROFILE_OFF)
    profile_on = entry.data.get(CONF_PROFILE_ON, DEFAULT_PROFILE_ON)
    device_list = entry.data.get(CONF_DEVICES, DEFAULT_DEVICES)
    use_devices = entry.data.get(CONF_USE_DEVICES, DEFAULT_USE_DEVICES)
    use_wifi = entry.data.get(CONF_USE_WIFI, DEFAULT_USE_WIFI)
    use_port = entry.data.get(CONF_USE_PORT, DEFAULT_USE_PORT)
    use_deflections = entry.data.get(CONF_USE_DEFLECTIONS, DEFAULT_USE_DEFLECTIONS)

    fritz_tools = await hass.async_add_executor_job(lambda: FritzBoxTools(
        host=host,
        port=port,
        username=username,
        password=password,
        profile_on=profile_on,
        profile_off=profile_off,
        device_list=device_list,
        use_wifi=use_wifi,
        use_deflections=use_deflections,
        use_port=use_port,
        use_devices=use_devices,
    ))

    hass.data.setdefault(DOMAIN, {})[DATA_FRITZ_TOOLS_INSTANCE] = fritz_tools

    hass.services.async_register(
        DOMAIN, SERVICE_RECONNECT, fritz_tools.service_reconnect_fritzbox
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REBOOT, fritz_tools.service_reboot_fritzbox
    )

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, domain)
        )

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigType) -> bool:
    """Unload FRITZ!Box Tools config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_RECONNECT)
    hass.services.async_remove(DOMAIN, SERVICE_REBOOT)

    for domain in SUPPORTED_DOMAINS:
        await hass.config_entries.async_forward_entry_unload(entry, domain)

    del hass.data[DOMAIN]

    return True


class FritzBoxTools(object):
    """
    Attention: The initialization of the class performs sync I/O. If you're calling this from within Home Assistant,
    wrap it in await self.hass.async_add_executor_job(lambda: FritzBoxTools(...))
    """
    def __init__(
        self,
        password,
        username = DEFAULT_USERNAME,
        host = DEFAULT_HOST,
        port=DEFAULT_PORT,
        profile_on = DEFAULT_PROFILE_ON,
        profile_off = DEFAULT_PROFILE_OFF,
        device_list = DEFAULT_DEVICES,
        use_port = DEFAULT_USE_PORT,
        use_deflections = DEFAULT_USE_DEFLECTIONS,
        use_wifi = DEFAULT_USE_WIFI,
        use_devices = DEFAULT_USE_DEVICES,
    ):
        # pylint: disable=import-error
        from fritzconnection import FritzConnection
        from fritzconnection.lib.fritzstatus import FritzStatus
        from fritz_switch_profiles import FritzProfileSwitch

        # general timeout for all requests to the router. Some calls need quite some time.
        self.connection = FritzConnection(
            address=host, port=port, user=username, password=password, timeout=30.0
        )

        if device_list != DEFAULT_DEVICES:
            self.profile_switch = FritzProfileSwitch(
                "http://" + host, username, password
            )

        self.fritzstatus = FritzStatus(fc=self.connection)
        self.ha_ip = get_local_ip()
        self.profile_on = profile_on
        self.profile_off = profile_off
        self.profile_last_updated = time.time()
        self.device_list = device_list

        self.username = username
        self.password = password
        self.port = port
        self.host = host

        self.use_wifi = use_wifi
        self.use_port = use_port
        self.use_deflections = use_deflections
        self.use_devices = use_devices

        self._unique_id = self.connection.call_action("DeviceInfo:1", "GetInfo")[
            "NewSerialNumber"
        ]
        self._device_info = self._fetch_device_info()

    async def async_update_profiles(self, hass):
        if time.time() > self.profile_last_updated + 5:
            # do not update profiles too often (takes too long...)!
            await hass.async_add_executor_job(self.profile_switch.fetch_profiles)
            await hass.async_add_executor_job(self.profile_switch.fetch_devices)
            await hass.async_add_executor_job(self.profile_switch.fetch_device_profiles)
            self.profile_last_updated = time.time()

    def service_reconnect_fritzbox(self, call) -> None:
        _LOGGER.info("Reconnecting the fritzbox.")
        self.connection.reconnect()

    def service_reboot_fritzbox(self, call) -> None:
        _LOGGER.info("Rebooting the fritzbox.")
        self.connection.call_action("DeviceConfig1", "Reboot")

    def is_ok(self):
        # TODO for future: do more of the async_setup_entry checks right here

        from fritzconnection.core.exceptions import FritzConnectionException

        try:
            _ = self.connection.call_action(
                "Layer3Forwarding:1", "GetDefaultConnectionService"
            )["NewDefaultConnectionService"]
            return True, ""
        except FritzConnectionException:
            return False, "connection_error"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def device_info(self):
        return self._device_info

    def _fetch_device_info(self):
        info = self.connection.call_action("DeviceInfo:1", "GetInfo")
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "name": info.get("NewProductClass"),
            "manufacturer": "AVM",
            "model": info.get("NewModelName"),
            "sw_version": info.get("NewSoftwareVersion"),
        }
