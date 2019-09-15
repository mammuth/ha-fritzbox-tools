import logging

from homeassistant.helpers import discovery

DOMAIN = 'fritzbox_tools'
SUPPORTED_DOMAINS = ["switch"]
REQUIREMENTS = ['fritzconnection==0.8.2']

DATA_FRITZ_TOOLS_INSTANCE = 'fritzbox_tools_instance'

_LOGGER = logging.getLogger(__name__)


def setup(hass, config):
    _LOGGER.debug('Setting up fritzbox_tools component')
    host = config[DOMAIN].get('host', '169.254.1.1')
    port = config[DOMAIN].get('port', 49000)
    username = config[DOMAIN].get('username', '')
    password = config[DOMAIN].get('password', None)

    if not password:
        raise ValueError('Password is not set in configuration')

    fritz_tools = FritzBoxTools(
        host=host,
        port=port,
        username=username,
        password=password
    )

    hass.data.setdefault(DOMAIN, {})[DATA_FRITZ_TOOLS_INSTANCE] = fritz_tools

    hass.services.register(DOMAIN, 'reconnect', fritz_tools.reconnect_fritzbox)

    # Load the other platforms like switch
    for domain in SUPPORTED_DOMAINS:
        discovery.load_platform(hass, domain, DOMAIN, {}, config)

    return True


class FritzBoxTools(object):

    def __init__(self, host, port, username, password):
        # pylint: disable=import-error
        import fritzconnection as fc
        self._connection = fc.FritzConnection(
            address=host,
            port=port,
            user=username,
            password=password
        )

    def reconnect_fritzbox(self, call) -> None:
        _LOGGER.info('Reconnecting the fritzbox.')
        self._connection.reconnect()

    def _handle_guestwifi_turn_on_off(self, turn_on: bool) -> bool:
        # pylint: disable=import-error
        from fritzconnection.fritzconnection import ServiceError, ActionError
        new_state = '1' if turn_on else '0'
        try:
            self._connection.call_action('WLANConfiguration:3', 'SetEnable', NewEnable=new_state)
        except (ServiceError, ActionError) as e:
            _LOGGER.error('Home Assistant cannot call the wished service on the FRITZ!Box. '
                          'Are credentials, address and port correct?')
            _LOGGER.debug(e)
            return False
        else:
            return True
