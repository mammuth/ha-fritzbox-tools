"""Constants for the FRITZ!Box Tools integration."""

DOMAIN = "fritzbox_tools"
DATA_FRITZ_TOOLS_INSTANCE = "fritzbox_tools_instance"
SUPPORTED_DOMAINS = ["switch", "binary_sensor"]

ATTR_HOST = "host"

CONF_PROFILES = "profiles"

CONF_USE_WIFI = "use_wifi"
CONF_USE_PORT = "use_port"
CONF_USE_DEFLECTIONS = "use_deflections"
CONF_USE_PROFILES = "use_profiles"

DEFAULT_HOST = "192.168.178.1"  # set to fritzbox default
DEFAULT_PORT = 49000  # set to fritzbox default
DEFAULT_USERNAME = ""  # set to fritzbox default?!

DEFAULT_USE_WIFI = True
DEFAULT_USE_PORT = True
DEFAULT_USE_DEFLECTIONS = True
DEFAULT_USE_PROFILES = True

DEFAULT_PROFILES = []

SERVICE_RECONNECT = "reconnect"
SERVICE_REBOOT = "reboot"

ERROR_CONNECTION_ERROR = "connection_error"
ERROR_CONNECTION_ERROR_PROFILES = "connection_error_profiles"
ERROR_PROFILE_NOT_FOUND = "profile_not_found"
