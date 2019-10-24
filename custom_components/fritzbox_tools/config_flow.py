"""Config flow to configure the fritzbox_tools integration."""
import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_PROFILE_ON,
    CONF_PROFILE_OFF,
    CONF_HOMEASSISTANT_IP,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_PROFILE_OFF,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_PORT,
)
from . import DATA_FRITZ_TOOLS_INSTANCE


_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class FritzBoxToolsFlowHandler(ConfigFlow):
    """Handle a Fritzbox Tools config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    _hassio_discovery = None

    def __init__(self):
        """Initialize Fritzbox Tools flow."""
        pass

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Optional(CONF_USERNAME): str,  # Does it work with empty username? else set Required
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

        fritzbox_tools = self.hass.data[DOMAIN][DATA_FRITZ_TOOLS_INSTANCE]
        success = await fritzbox_tools.is_ok()

        if not success:
            errors["base"] = "connection_error"
            return await self._show_setup_form(errors)

        return self.async_create_entry(
            title=user_input[CONF_HOST],
            data={
                CONF_HOST: user_input[CONF_HOST],
                CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                CONF_PORT: user_input[CONF_PORT],
                CONF_PROFILE_ON: user_input.get(CONF_PROFILE_ON),
                CONF_PROFILE_OFF: user_input.get(CONF_PROFILE_OFF),
                CONF_USERNAME: user_input.get(CONF_USERNAME),
                CONF_HOMEASSISTANT_IP: user_input.get(CONF_HOMEASSISTANT_IP)
            },
        )
