"""Config and options flow for the Anki integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnkiConnectClient, AnkiConnectError
from .const import (
    CONF_API_KEY,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_API_KEY, default=""): str,
    }
)


class AnkiConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Anki config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual host/port/name/api-key entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            if await self._async_reachable(user_input):
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME), data=user_input
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change host/port/name/api-key of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            if await self._async_reachable(user_input):
                # Keep the unique id in sync when host/port change. Passing the
                # entry's own new id avoids the self-collision that
                # _abort_if_unique_id_configured would raise here.
                return self.async_update_reload_and_abort(
                    entry,
                    data=user_input,
                    unique_id=f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}",
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, entry.data),
            errors=errors,
        )

    async def _async_reachable(self, user_input: dict[str, Any]) -> bool:
        client = AnkiConnectClient(
            user_input[CONF_HOST],
            user_input[CONF_PORT],
            async_get_clientsession(self.hass),
            api_key=user_input.get(CONF_API_KEY) or None,
        )
        try:
            # async_version raises AnkiConnectError on any failure (api.py wraps
            # aiohttp/timeout errors), so a clean return means we reached Anki.
            await client.async_version()
        except AnkiConnectError:
            return False
        return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AnkiConnectOptionsFlow:
        return AnkiConnectOptionsFlow()


class AnkiConnectOptionsFlow(OptionsFlow):
    """Options: polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    int, vol.Range(min=5)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
