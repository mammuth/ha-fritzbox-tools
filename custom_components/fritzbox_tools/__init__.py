"""Support for AVM Fritz!Box functions"""
import asyncio
import logging
import time

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_DEVICES, CONF_HOST, CONF_PASSWORD,
                                 CONF_PORT, CONF_USERNAME)
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import (CONF_HOMEASSISTANT_IP, CONF_PROFILE_OFF, CONF_PROFILE_ON,
                    DEFAULT_DEVICES, DEFAULT_HOMEASSISTANT_IP, DEFAULT_HOST,
                    DEFAULT_PORT, DEFAULT_PROFILE_OFF, DEFAULT_PROFILE_ON,
                    DOMAIN, SERVICE_RECONNECT, SUPPORTED_DOMAINS)

REQUIREMENTS = ['fritzconnection==0.8.4', 'fritz-switch-profiles==1.0.0']

DATA_FRITZ_TOOLS_INSTANCE = 'fritzbox_tools_instance'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT): cv.port,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOMEASSISTANT_IP): cv.string,
                vol.Optional(CONF_DEVICES): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_PROFILE_ON): cv.string,
                vol.Optional(CONF_PROFILE_OFF): cv.string,
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
    _LOGGER.debug('Setting up FRITZ!Box Tools component')
    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    ha_ip = entry.data.get(CONF_HOMEASSISTANT_IP, DEFAULT_HOMEASSISTANT_IP)
    profile_off = entry.data.get(CONF_PROFILE_OFF, DEFAULT_PROFILE_OFF)
    profile_on = entry.data.get(CONF_PROFILE_ON, DEFAULT_PROFILE_ON)
    device_list = entry.data.get(CONF_DEVICES, DEFAULT_DEVICES)

    fritz_tools = FritzBoxTools(
        host=host,
        port=port,
        username=username,
        password=password,
        ha_ip=ha_ip,
        profile_on=profile_on,
        profile_off=profile_off,
        device_list=device_list
    )

    hass.data.setdefault(DOMAIN, {})[DATA_FRITZ_TOOLS_INSTANCE] = fritz_tools

    hass.services.async_register(
        DOMAIN, SERVICE_RECONNECT, fritz_tools.service_reconnect_fritzbox)

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, domain)
        )

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigType) -> bool:
    """Unload FRITZ!Box Tools config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_RECONNECT)

    for domain in SUPPORTED_DOMAINS:
        await hass.config_entries.async_forward_entry_unload(entry, domain)

    del hass.data[DOMAIN]

    return True


class FritzBoxTools(object):

    def __init__(self, host, port, username, password, ha_ip, profile_on, profile_off, device_list):
        # pylint: disable=import-error
        import fritzconnection as fc
        from fritz_switch_profiles import FritzProfileSwitch
        self.connection = fc.FritzConnection(
            address=host,
            port=port,
            user=username,
            password=password
        )

        if profile_on is not None:
            self.profile_switch = FritzProfileSwitch(
                'http://' + host, username, password)

        self.fritzstatus = fc.FritzStatus(fc=self.connection)
        self.ha_ip = ha_ip
        self.profile_on = profile_on
        self.profile_off = profile_off
        self.profile_last_updated = time.time()
        self.device_list = device_list

    async def async_update_profiles(self):
        if time.time() > self.profile_last_updated + 5:
            # do not update profiles too often (takes too long...)!
            await asyncio.coroutine(self.profile_switch.fetch_profiles)()
            await asyncio.coroutine(self.profile_switch.fetch_devices)()
            await asyncio.coroutine(self.profile_switch.fetch_device_profiles)()
            self.profile_last_updated = time.time()

    def service_reconnect_fritzbox(self, call) -> None:
        _LOGGER.info('Reconnecting the fritzbox.')
        self.connection.reconnect()

    async def is_ok(self):
        # TODO for future: do more of the async_setup_entry checks right here

        from fritzconnection.fritzconnection import AuthorizationError
        try:
            _ = self.connection.call_action(
                'Layer3Forwarding:1',
                'GetDefaultConnectionService'
            )['NewDefaultConnectionService']
            return True, ""
        except AuthorizationError:
            return False, "connection_error"

    @property
    def unique_id(self):
        serial = self.connection.call_action("DeviceInfo:1", "GetInfo")[
            "NewSerialNumber"]
        return serial

    @property
    def device_info(self):
        info = self.connection.call_action("DeviceInfo:1", "GetInfo")
        return {
            'identifiers': {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            'name': info.get("NewProductClass"),
            'manufacturer': "AVM",
            'model': info.get("NewModelName"),
            'sw_version': info.get("NewSoftwareVersion")
        }
