"""Support for AVM Fritz!Box classes."""
import logging
import socket

import voluptuous as vol

from homeassistant.const import (
    CONF_DEVICES,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import get_local_ip

from .const import (
    ATTR_HOST,
    CONF_PROFILES,
    CONF_USE_DEFLECTIONS,
    CONF_USE_PORT,
    CONF_USE_PROFILES,
    CONF_USE_WIFI,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_PROFILES,
    DEFAULT_USE_DEFLECTIONS,
    DEFAULT_USE_PORT,
    DEFAULT_USE_PROFILES,
    DEFAULT_USE_WIFI,
    DEFAULT_USERNAME,
    DOMAIN,
    ERROR_CONNECTION_ERROR,
    ERROR_CONNECTION_ERROR_PROFILES,
    ERROR_PROFILE_NOT_FOUND,
)

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
                                    vol.Optional(CONF_PROFILES): vol.All(
                                        cv.ensure_list, [cv.string]
                                    ),
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


class FritzBoxTools:
    """FrtizBoxTools class."""

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
        """Initialize FritzboxTools class."""
        # pylint: disable=import-error
        from fritzconnection import FritzConnection
        from fritzconnection.core.exceptions import FritzConnectionException
        from fritzconnection.lib.fritzstatus import FritzStatus
        from fritzprofiles import FritzProfileSwitch

        # general timeout for all requests to the router. Some calls need quite some time.

        try:
            self.connection = FritzConnection(
                address=host, port=port, user=username, password=password, timeout=60.0
            )
            if profile_list != DEFAULT_PROFILES:
                self.profile_switch = {
                    profile: FritzProfileSwitch(
                        "http://" + host, username, password, profile
                    )
                    for profile in profile_list
                }
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
            self.error = ERROR_CONNECTION_ERROR
        except PermissionError:
            self.success = False
            self.error = ERROR_CONNECTION_ERROR_PROFILES
        except AttributeError:
            self.success = False
            self.error = ERROR_PROFILE_NOT_FOUND

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
        """Define service reconnect."""
        _LOGGER.info("Reconnecting the fritzbox.")
        self.connection.reconnect()

    def service_reboot_fritzbox(self) -> None:
        """Define service reboot."""
        _LOGGER.info("Rebooting the fritzbox.")
        self.connection.call_action("DeviceConfig1", "Reboot")

    def is_ok(self):
        """Return status."""
        return self.success, self.error

    @property
    def unique_id(self):
        """Return unique id."""
        return self._unique_id

    @property
    def fritzbox_model(self):
        """Return model."""
        return self._device_info["model"].replace("FRITZ!Box ", "")

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    def _fetch_device_info(self):
        """Fetch device info."""
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
