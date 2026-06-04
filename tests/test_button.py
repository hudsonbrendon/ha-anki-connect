"""Tests for Anki buttons."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData


async def _setup(hass) -> AsyncMock:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)
    request = AsyncMock(return_value=None)
    with patch(
        "custom_components.anki_connect.coordinator.AnkiDataUpdateCoordinator._async_update_data",
        return_value=AnkiData(available=True, version=6),
    ), patch(
        "custom_components.anki_connect.api.AnkiConnectClient.request", new=request
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    # Persist the mock on the live coordinator client so button presses use it.
    entry.runtime_data.client.request = request
    # Also prevent real coordinator refreshes (triggered by async_press) from
    # making extra API calls that would obscure the button's own request.
    entry.runtime_data._async_update_data = AsyncMock(
        return_value=AnkiData(available=True, version=6)
    )
    return request


async def test_sync_button_sends_sync_action(hass):
    request = await _setup(hass)
    request.reset_mock()
    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.anki_sync"},
        blocking=True,
    )
    request.assert_awaited_with("sync")


async def test_check_database_button(hass):
    request = await _setup(hass)
    request.reset_mock()
    await hass.services.async_call(
        "button",
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.anki_check_database"},
        blocking=True,
    )
    request.assert_awaited_with("guiCheckDatabase")
