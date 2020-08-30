"""Support for AVM Fritz!Box functions"""
import asyncio
import logging
import time

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import get_local_ip

from .const import (
    DEFAULT_PROFILES,
    DEFAULT_HOST,
    DEFAULT_USERNAME,
    DEFAULT_PORT,
    DOMAIN,
    SERVICE_RECONNECT,
    SERVICE_REBOOT,
    SUPPORTED_DOMAINS,
    CONF_USE_WIFI,
    CONF_USE_PROFILES,
    CONF_USE_DEFLECTIONS,
    CONF_USE_PORT,
    CONF_PROFILES,
    DEFAULT_USE_WIFI,
    DEFAULT_USE_PROFILES,
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
                vol.Optional(CONF_PROFILES): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_USE_PROFILES): cv.string,
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
    profile_list = entry.data.get(CONF_PROFILES, DEFAULT_PROFILES)
    use_profiles = entry.data.get(CONF_USE_PROFILES, DEFAULT_USE_PROFILES)
    use_wifi = entry.data.get(CONF_USE_WIFI, DEFAULT_USE_WIFI)
    use_port = entry.data.get(CONF_USE_PORT, DEFAULT_USE_PORT)
    use_deflections = entry.data.get(CONF_USE_DEFLECTIONS, DEFAULT_USE_DEFLECTIONS)

    fritz_tools = await hass.async_add_executor_job(lambda: FritzBoxTools(
        host=host,
        port=port,
        username=username,
        password=password,
        profile_list=profile_list,
        use_wifi=use_wifi,
        use_deflections=use_deflections,
        use_port=use_port,
        use_profiles=use_profiles,
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
        profile_list = DEFAULT_PROFILES,
        use_port = DEFAULT_USE_PORT,
        use_deflections = DEFAULT_USE_DEFLECTIONS,
        use_wifi = DEFAULT_USE_WIFI,
        use_profiles = DEFAULT_USE_PROFILES,
    ):
        # pylint: disable=import-error
        from fritzconnection import FritzConnection
        from fritzconnection.lib.fritzstatus import FritzStatus
        from fritzprofiles import FritzProfileSwitch
        from fritzconnection.core.exceptions import FritzConnectionException
        
        # general timeout for all requests to the router. Some calls need quite some time.
        
        try:
            self.connection = FritzConnection(
                address=host, port=port, user=username, password=password, timeout=60.0
            )
            if profile_list != DEFAULT_PROFILES:
                self.profile_switch = {profile: FritzProfileSwitch(
                    "http://" + host, username, password, profile
                ) for profile in profile_list}
            else:
                self.profile_switch={}

            self.fritzstatus = FritzStatus(fc=self.connection)
            self._unique_id = self.connection.call_action("DeviceInfo:1", "GetInfo")[
                "NewSerialNumber"
            ]
            self._device_info = self._fetch_device_info()
            self.success = True
            self.error = False
        except FritzConnectionException:
            self.success = False
            self.error = "connection_error"
        except PermissionError:
            self.success = False
            self.error = "connection_error_profiles"
        except AttributeError:
            self.success = False
            self.error = "profile_not_found"
            
            
        self.ha_ip = get_local_ip()    
        self.profile_list = profile_list

        self.username = username
        self.password = password
        self.port = port
        self.host = host

        self.use_wifi = use_wifi
        self.use_port = use_port
        self.use_deflections = use_deflections
        self.use_profiles = use_profiles

    def service_reconnect_fritzbox(self, call) -> None:
        _LOGGER.info("Reconnecting the fritzbox.")
        self.connection.reconnect()

    def service_reboot_fritzbox(self, call) -> None:
        _LOGGER.info("Rebooting the fritzbox.")
        self.connection.call_action("DeviceConfig1", "Reboot")

    def is_ok(self):
        return self.success, self.error
        
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
