"""Support for AVM Fritz!Box functions"""
import asyncio
import logging
import socket
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
ATTR_HOST = "host"

_LOGGER = logging.getLogger(__name__)


def ensure_unique_hosts(value):
    """Validate that all configs have a unique host."""
    vol.Schema(vol.Unique("duplicate host entries found"))(
        [socket.gethostbyname(entry[CONF_HOST]) for entry in value]
    )
    return value


CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {
            DOMAIN: vol.Schema(
                {
                    vol.Required(CONF_DEVICES): vol.All(
                        cv.ensure_list,
                        [
                            vol.Schema(
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
                        ],
                        ensure_unique_hosts,
                    )
                }
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SCHEMA = vol.Schema({vol.Required(ATTR_HOST): cv.string})

async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Setup FRITZ!Box Tools component"""
    if DOMAIN in config:
        for entry_config in config[DOMAIN][CONF_DEVICES]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": "import"}, data=entry_config
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

    hass.data.setdefault(DOMAIN, {DATA_FRITZ_TOOLS_INSTANCE: {}, CONF_DEVICES: set()})
    hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE][host] = fritz_tools
    hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE][entry.entry_id] = fritz_tools

    setup_hass_services(hass)

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, domain)
        )

    return True

def setup_hass_services(hass):
    """Home Assistant services."""

    def reboot(call):
        """Reboot fritzbox"""
        host = call.data.get(ATTR_HOST)
        fritztools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE].get(host,None)
        if fritztools is None:
            _LOGGER.error(f"{SERVICE_REBOOT}: Please supply a valid hostname of a configured fritzbox for the service (e.g. 192.168.178.1)")
        else:
            fritztools.service_reboot_fritzbox()

    def reconnect(call):
        """Reboot fritzbox"""
        host = call.data.get(ATTR_HOST)
        fritztools = hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE].get(host,None)
        if fritztools is None:
            _LOGGER.error(f"{SERVICE_RECONNECT}: Please supply a valid hostname of a configured fritzbox for the service (e.g. 192.168.178.1)")
        else:
            fritztools.service_reconnect_fritzbox()

    hass.services.async_register(
        DOMAIN,SERVICE_RECONNECT, reconnect, schema=SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REBOOT, reboot, schema=SERVICE_SCHEMA,
    )

async def async_unload_entry(hass: HomeAssistantType, entry: ConfigType) -> bool:
    """Unload FRITZ!Box Tools config entry."""
    hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE].pop(entry.data.get(CONF_HOST))
    hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE].pop(entry.entry_id)
    hass.services.async_remove(DOMAIN, SERVICE_RECONNECT)
    hass.services.async_remove(DOMAIN, SERVICE_REBOOT)

    for domain in SUPPORTED_DOMAINS:
        await hass.config_entries.async_forward_entry_unload(entry, domain)

    return True


class FritzBoxTools(object):
    """
    Attention: The initialization of the class performs sync I/O. If you're calling this from within Home Assistant,
    wrap it in await self.hass.async_add_executor_job(lambda: FritzBoxTools(...))
    """

    def __init__(
            self,
            password,
            username=DEFAULT_USERNAME,
            host=DEFAULT_HOST,
            port=DEFAULT_PORT,
            profile_list=DEFAULT_PROFILES,
            use_port=DEFAULT_USE_PORT,
            use_deflections=DEFAULT_USE_DEFLECTIONS,
            use_wifi=DEFAULT_USE_WIFI,
            use_profiles=DEFAULT_USE_PROFILES,
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
                self.profile_switch = {}

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

    def service_reconnect_fritzbox(self) -> None:
        _LOGGER.info("Reconnecting the fritzbox.")
        self.connection.reconnect()

    def service_reboot_fritzbox(self) -> None:
        _LOGGER.info("Rebooting the fritzbox.")
        self.connection.call_action("DeviceConfig1", "Reboot")

    def is_ok(self):
        return self.success, self.error

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def fritzbox_model(self):
        return self._device_info["model"].replace("FRITZ!Box ", "")

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
            "name": info.get("NewModelName"),
            "manufacturer": "AVM",
            "model": info.get("NewModelName"),
            "sw_version": info.get("NewSoftwareVersion"),
        }
