"""Constants for the FRITZ!Box Tools integration."""

DOMAIN = "fritzbox_tools"
SUPPORTED_DOMAINS = ["switch", "binary_sensor"]

CONF_PROFILE_ON = "profile_on"
CONF_PROFILE_OFF = "profile_off"

CONF_USE_WIFI = "use_wifi"
CONF_USE_PORT = "use_port"
CONF_USE_DEFLECTIONS = "use_deflections"
CONF_USE_DEVICES = "use_devices"

DEFAULT_HOST = "192.168.178.1"  # set to fritzbox default
DEFAULT_PORT = 49000  # set to fritzbox default
DEFAULT_USERNAME = ""  # set to fritzbox default?!

DEFAULT_USE_WIFI = True
DEFAULT_USE_PORT = True
DEFAULT_USE_DEFLECTIONS = True
DEFAULT_USE_DEVICES = True

DEFAULT_PROFILE_ON = "Standard"
DEFAULT_PROFILE_OFF = "Gesperrt"
DEFAULT_DEVICES = []

SERVICE_RECONNECT = "reconnect"
