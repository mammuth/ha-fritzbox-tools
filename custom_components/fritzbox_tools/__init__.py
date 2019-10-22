import logging
import time
from homeassistant.helpers import discovery

from homeassistant.const import (
    CONF_DEVICES,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_PORT
)

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

DOMAIN = 'fritzbox_tools'
SUPPORTED_DOMAINS = ['switch', 'sensor']

CONF_PROFILE_ON = 'profile_on'
CONF_PROFILE_OFF = 'profile_off'
CONF_HOMEASSISTANT_IP = 'homeassistant_ip'

DEFAULT_PROFILE_OFF = 'Gesperrt'
DEFAULT_HOST = '192.168.178.1' #set to fritzbox default
DEFAULT_PORT = 49000 #set to fritzbox default
DEFAULT_USERNAME = '' #set to fritzbox default?!
DEFAULT_PROFILE_ON = None
DEFAULT_DEVICES = None
DEFAULT_HOMEASSISTANT_IP = None

SERVICE_RECONNECT = 'reconnect'

CONF_HOMEASSISTANT_IP

REQUIREMENTS = ['fritzconnection==0.8.4', 'fritz-switch-profiles==1.0.0']


DATA_FRITZ_TOOLS_INSTANCE = 'fritzbox_tools_instance'

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT): cv.port,
                vol.Optional(CONF_USERNAME): cv.string, # Does it work with empty username? else set Required
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


def setup(hass, config):
    _LOGGER.debug('Setting up fritzbox_tools component')
    host = config[DOMAIN].get(CONF_HOST, DEFAULT_HOST)
    port = config[DOMAIN].get(CONF_PORT, DEFAULT_PORT)
    username = config[DOMAIN].get(CONF_USERNAME, DEFAULT_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    ha_ip = config[DOMAIN].get(CONF_HOMEASSISTANT_IP, DEFAULT_HOMEASSISTANT_IP)
    profile_off = config[DOMAIN].get(CONF_PROFILE_OFF, DEFAULT_PROFILE_OFF)
    profile_on = config[DOMAIN].get(CONF_PROFILE_ON, DEFAULT_PROFILE_ON)
    device_list = config[DOMAIN].get(CONF_DEVICES, DEFAULT_DEVICES)

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

    hass.services.register(DOMAIN, SERVICE_RECONNECT, fritz_tools.service_reconnect_fritzbox)

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        discovery.load_platform(hass, domain, DOMAIN, {}, config)

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
        self.profile_switch = FritzProfileSwitch("http://"+host, username, password)
        self.fritzstatus = fc.FritzStatus(fc=self.connection)
        self.ha_ip = ha_ip
        self.profile_on = profile_on
        self.profile_off = profile_off
        self.profile_last_updated = time.time()
        self.device_list = device_list

    def update_profiles(self):
        if time.time() > self.profile_last_updated + 5:
            # do not update profiles too often (takes too long...)!
            self.profile_switch.fetch_profiles()
            self.profile_switch.fetch_devices()
            self.profile_switch.fetch_device_profiles()
            self.profile_last_updated = time.time()

    def service_reconnect_fritzbox(self, call) -> None:
        _LOGGER.info('Reconnecting the fritzbox.')
        self.connection.reconnect()
