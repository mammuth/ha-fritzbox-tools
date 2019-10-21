import logging
import time
import asyncio
from homeassistant.helpers import discovery

DOMAIN = 'fritzbox_tools'
SUPPORTED_DOMAINS = ['switch', 'sensor']

REQUIREMENTS = ['fritzconnection==0.8.4', 'fritz-switch-profiles==1.0.0']


DATA_FRITZ_TOOLS_INSTANCE = 'fritzbox_tools_instance'

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    _LOGGER.debug('Setting up fritzbox_tools component')
    host = config[DOMAIN].get('host', '169.254.1.1')
    port = config[DOMAIN].get('port', 49000)
    username = config[DOMAIN].get('username', '')
    password = config[DOMAIN].get('password', None)
    ha_ip = config[DOMAIN].get('homeassistant_ip', None)
    profile_off = config[DOMAIN].get('profile_off', 'Gesperrt')
    profile_on = config[DOMAIN].get('profile_on', None)
    device_list = config[DOMAIN].get('device_list', None)

    if not password:
        raise ValueError('Password is not set in configuration')

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

    hass.services.async_register(DOMAIN, 'reconnect', fritz_tools.service_reconnect_fritzbox)

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        await discovery.async_load_platform(hass, domain, DOMAIN, {}, config)

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
            self.profile_switch = FritzProfileSwitch("http://"+host, username, password)
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
