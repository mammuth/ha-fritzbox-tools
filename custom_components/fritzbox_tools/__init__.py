import logging

from homeassistant.helpers import discovery

DOMAIN = 'fritzbox_tools'
SUPPORTED_DOMAINS = ['switch', 'sensor']
REQUIREMENTS = ['fritzconnection==0.8.2']

DATA_FRITZ_TOOLS_INSTANCE = 'fritzbox_tools_instance'

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    _LOGGER.debug('Setting up fritzbox_tools component')
    host = config[DOMAIN].get('host', '169.254.1.1')
    port = config[DOMAIN].get('port', 49000)
    username = config[DOMAIN].get('username', '')
    password = config[DOMAIN].get('password', None)
    ha_ip = config[DOMAIN].get('homeassistant_ip', None)

    if not password:
        raise ValueError('Password is not set in configuration')

    fritz_tools = FritzBoxTools(
        host=host,
        port=port,
        username=username,
        password=password,
        ha_ip=ha_ip
    )

    hass.data.setdefault(DOMAIN, {})[DATA_FRITZ_TOOLS_INSTANCE] = fritz_tools

    hass.services.register(DOMAIN, 'reconnect', fritz_tools.service_reconnect_fritzbox)

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        discovery.load_platform(hass, domain, DOMAIN, {}, config)

    return True


class FritzBoxTools(object):

    def __init__(self, host, port, username, password, ha_ip):
        # pylint: disable=import-error
        import fritzconnection as fc
        self.connection = fc.FritzConnection(
            address=host,
            port=port,
            user=username,
            password=password
        )
        self.fritzstatus = fc.FritzStatus(fc=self.connection)
        self.ha_ip = ha_ip

    def service_reconnect_fritzbox(self, call) -> None:
        _LOGGER.info('Reconnecting the fritzbox.')
        self.connection.reconnect()
