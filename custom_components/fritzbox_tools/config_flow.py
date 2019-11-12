"""Config flow to configure the FRITZ!Box Tools integration."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_PROFILE_ON,
    CONF_PROFILE_OFF,
    CONF_HOMEASSISTANT_IP,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_PROFILE_OFF,
    DEFAULT_DEVICES,
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

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_HOMEASSISTANT_IP): str,
                    vol.Optional(CONF_PROFILE_ON): str,
                    vol.Optional(CONF_PROFILE_OFF, default=DEFAULT_PROFILE_OFF): str
                }
            ),
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}

        host = user_input.get(CONF_HOST, DEFAULT_HOST)
        port = user_input.get(CONF_PORT, DEFAULT_PORT)
        username = user_input.get(CONF_USERNAME)
        password = user_input.get(CONF_PASSWORD)

        fritz_tools = FritzBoxTools(
            host=host,
            port=port,
            username=username,
            password=password,
            profile_on=None,
            profile_off=None,
            device_list=None,
            ha_ip=None
        )
        success = await fritz_tools.is_ok()

        if not success:
            errors["base"] = "connection_error"
            return await self._show_setup_form(errors)

        return self.async_create_entry(
            title="FRITZ!Box Tools",
            data={
                CONF_HOST: user_input.get(CONF_HOST),
                CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                CONF_PORT: user_input.get(CONF_PORT),
                CONF_PROFILE_ON: user_input.get(CONF_PROFILE_ON),
                CONF_PROFILE_OFF: user_input.get(CONF_PROFILE_OFF),
                CONF_USERNAME: user_input.get(CONF_USERNAME),
                CONF_HOMEASSISTANT_IP: user_input.get(CONF_HOMEASSISTANT_IP),
                CONF_DEVICES: user_input.get(CONF_DEVICES)
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
        return await self.async_step_user(user_input=import_config)
