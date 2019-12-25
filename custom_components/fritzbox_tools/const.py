"""Constants for the FRITZ!Box Tools integration."""

DOMAIN = "fritzbox_tools"
SUPPORTED_DOMAINS = ["switch", "binary_sensor"]

CONF_PROFILE_ON = "profile_on"
CONF_PROFILE_OFF = "profile_off"
CONF_HOMEASSISTANT_IP = "homeassistant_ip"

DEFAULT_HOST = "192.168.178.1"  # set to fritzbox default
DEFAULT_PORT = 49000  # set to fritzbox default
DEFAULT_USERNAME = ""  # set to fritzbox default?!

DEFAULT_PROFILE_ON = "Standard"
DEFAULT_PROFILE_OFF = "Gesperrt"
DEFAULT_DEVICES = []

DEFAULT_HOMEASSISTANT_IP = None

SERVICE_RECONNECT = "reconnect"
