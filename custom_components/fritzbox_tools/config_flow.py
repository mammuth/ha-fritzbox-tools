"""Config flow to configure the FRITZ!Box Tools integration."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_PROFILE_ON,
    CONF_PROFILE_OFF,
    CONF_USE_DEFLECTIONS,
    CONF_USE_DEVICES,
    CONF_USE_WIFI,
    CONF_USE_PORT,
    DEFAULT_USERNAME,
    DEFAULT_DEVICES,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_PROFILE_ON,
    DEFAULT_PROFILE_OFF,
    DEFAULT_USE_DEFLECTIONS,
    DEFAULT_USE_WIFI,
    DEFAULT_USE_DEVICES,
    DEFAULT_USE_PORT,
    SUPPORTED_DOMAINS,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_PORT,
    CONF_DEVICES,
)

from . import FritzBoxTools, CONFIG_SCHEMA


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class FritzBoxToolsFlowHandler(ConfigFlow):
    """Handle a FRITZ!Box Tools config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    _hassio_discovery = None

    def __init__(self):
        """Initialize FRITZ!Box Tools flow."""
        pass

    async def _show_setup_form_init(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="start_config",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors or {},
        )

    async def _show_setup_form_devices(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="setup_devices",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PROFILE_ON, default=DEFAULT_PROFILE_ON): str,
                    vol.Optional(CONF_PROFILE_OFF, default=DEFAULT_PROFILE_OFF): str,
                    vol.Optional(CONF_DEVICES): str,
                }
            ),
            errors=errors or {},
        )

    async def _show_setup_form_options(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="setup_options",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USE_WIFI, default=DEFAULT_USE_WIFI): bool,
                    vol.Required(CONF_USE_PORT, default=DEFAULT_USE_PORT): bool,
                    vol.Required(CONF_USE_DEVICES, default=DEFAULT_USE_DEVICES): bool,
                    vol.Required(CONF_USE_DEFLECTIONS, default=DEFAULT_USE_DEFLECTIONS): bool,
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return await self._show_setup_form_init()

    async def async_step_start_config(self, user_input=None):
            if user_input is None:
                return await self._show_setup_form_init()

            errors = {}

            host = user_input.get(CONF_HOST, DEFAULT_HOST)
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            self.fritz_tools = await self.hass.async_add_executor_job(lambda: FritzBoxTools(
                host=host,
                port=port,
                username=username,
                password=password,
                profile_on=None,
                profile_off=None,
                device_list=[]
            ))
            success, error = await self.hass.async_add_executor_job(self.fritz_tools.is_ok)

            if not success:
                errors["base"] = error
                return await self._show_setup_form_init(errors)

            return await self._show_setup_form_options(errors)

    async def async_step_setup_options(self, user_input=None):
        self._use_port = user_input.get(CONF_USE_PORT,DEFAULT_USE_PORT)
        self._use_deflections = user_input.get(CONF_USE_DEFLECTIONS,DEFAULT_USE_DEFLECTIONS)
        self._use_wifi = user_input.get(CONF_USE_WIFI,DEFAULT_USE_WIFI)
        self._use_devices = user_input.get(CONF_USE_DEVICES, DEFAULT_USE_DEVICES)

        if self._use_devices:
            errors = {}
            return await self._show_setup_form_devices(errors)
        else:
            devices = []
            return self.async_create_entry(
                title="FRITZ!Box Tools",
                data={
                    CONF_HOST: self.fritz_tools.host,
                    CONF_PASSWORD: self.fritz_tools.password,
                    CONF_PORT: self.fritz_tools.port,
                    CONF_PROFILE_ON: DEFAULT_PROFILE_ON,
                    CONF_PROFILE_ON: DEFAULT_PROFILE_OFF,
                    CONF_USERNAME: self.fritz_tools.username,
                    CONF_DEVICES: devices,
                    CONF_USE_WIFI: self._use_wifi,
                    CONF_USE_DEFLECTIONS: self._use_deflections,
                    CONF_USE_PORT: self._use_port,
                    CONF_USE_DEVICES: self._use_devices,
                },
            )


    async def async_step_setup_devices(self, user_input=None):
        devices = user_input.get(CONF_DEVICES,DEFAULT_DEVICES)
        if isinstance(devices, str):
            devices = devices.replace(' ', '').split(',')

        return self.async_create_entry(
            title="FRITZ!Box Tools",
            data={
                CONF_HOST: self.fritz_tools.host,
                CONF_PASSWORD: self.fritz_tools.password,
                CONF_PORT: self.fritz_tools.port,
                CONF_PROFILE_ON: user_input.get(CONF_PROFILE_ON, DEFAULT_PROFILE_ON),
                CONF_PROFILE_OFF: user_input.get(CONF_PROFILE_OFF, DEFAULT_PROFILE_OFF),
                CONF_USERNAME: self.fritz_tools.username,
                CONF_DEVICES: devices,
                CONF_USE_WIFI: self._use_wifi,
                CONF_USE_DEFLECTIONS: self._use_deflections,
                CONF_USE_PORT: self._use_port,
                CONF_USE_DEVICES: self._use_devices,
            },
        )


    async def async_step_import(self, import_config):
        """Import a FRITZ!Box Tools as a config entry.

        This flow is triggered by `async_setup` for configured devices.
        This flow is also triggered by `async_step_discovery`.

        This will execute for any complete
        configuration.
        """
        self.import_schema = CONFIG_SCHEMA

        errors = {}

        host = import_config.get(CONF_HOST, DEFAULT_HOST)
        port = import_config.get(CONF_PORT, DEFAULT_PORT)
        username = import_config.get(CONF_USERNAME)
        password = import_config.get(CONF_PASSWORD)
        devices = import_config.get(CONF_DEVICES,DEFAULT_DEVICES)

        if isinstance(devices, str):
            devices = devices.replace(" ", "").split(",")

        fritz_tools = await self.hass.async_add_executor_job(lambda: FritzBoxTools(
            host=host,
            port=port,
            username=username,
            password=password,
            profile_on=None,
            profile_off=None,
            device_list=[],
        ))
        success, error = await self.hass.async_add_executor_job(self.fritz_tools.is_ok)

        if not success:
            _LOGGER.error('Import of config failed. Check your fritzbox credentials',error)

        return self.async_create_entry(
            title="FRITZ!Box Tools",
            data={
                CONF_HOST: host,
                CONF_PASSWORD: password,
                CONF_PORT: port,
                CONF_PROFILE_ON: import_config.get(CONF_PROFILE_ON, DEFAULT_PROFILE_ON),
                CONF_PROFILE_OFF: import_config.get(CONF_PROFILE_OFF, DEFAULT_PROFILE_OFF),
                CONF_USERNAME: username,
                CONF_DEVICES: devices,
                CONF_USE_WIFI: DEFAULT_USE_WIFI,
                CONF_USE_DEFLECTIONS: DEFAULT_USE_DEFLECTIONS,
                CONF_USE_PORT: DEFAULT_USE_PORT,
                CONF_USE_DEVICES: DEFAULT_USE_DEVICES,
            },
        )
