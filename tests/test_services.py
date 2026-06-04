"""Tests for Anki services."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData


async def _setup(hass) -> tuple[str, AsyncMock]:
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
    # Persist the mock on the live coordinator client so service calls use it.
    entry.runtime_data.client.request = request
    return entry.entry_id, request


async def test_generic_api_service_returns_result(hass):
    entry_id, request = await _setup(hass)
    request.reset_mock()
    request.return_value = ["Default"]
    response = await hass.services.async_call(
        DOMAIN,
        "api",
        {"config_entry_id": entry_id, "action": "deckNames"},
        blocking=True,
        return_response=True,
    )
    request.assert_awaited_with("deckNames")
    assert response == {"result": ["Default"]}


async def test_api_service_forwards_params(hass):
    entry_id, request = await _setup(hass)
    request.reset_mock()
    await hass.services.async_call(
        DOMAIN,
        "api",
        {
            "config_entry_id": entry_id,
            "action": "getDeckStats",
            "params": {"decks": ["Default"]},
        },
        blocking=True,
        return_response=True,
    )
    request.assert_awaited_with("getDeckStats", decks=["Default"])


async def test_add_note_service(hass):
    entry_id, request = await _setup(hass)
    request.reset_mock()
    request.return_value = 1496198395707
    response = await hass.services.async_call(
        DOMAIN,
        "add_note",
        {
            "config_entry_id": entry_id,
            "deck": "Default",
            "model": "Basic",
            "fields": {"Front": "hola", "Back": "hello"},
            "tags": ["spanish"],
        },
        blocking=True,
        return_response=True,
    )
    request.assert_awaited_once()
    assert request.await_args[0][0] == "addNote"
    assert request.await_args[1]["note"]["deckName"] == "Default"
    assert request.await_args[1]["note"]["fields"] == {"Front": "hola", "Back": "hello"}
    assert response == {"result": 1496198395707}


async def test_find_notes_service(hass):
    entry_id, request = await _setup(hass)
    request.reset_mock()
    request.return_value = [1, 2, 3]
    response = await hass.services.async_call(
        DOMAIN,
        "find_notes",
        {"config_entry_id": entry_id, "query": "deck:Default"},
        blocking=True,
        return_response=True,
    )
    request.assert_awaited_with("findNotes", query="deck:Default")
    assert response == {"result": [1, 2, 3]}


async def test_sync_service_on_valid_entry(hass):
    entry_id, request = await _setup(hass)
    request.reset_mock()
    await hass.services.async_call(
        DOMAIN,
        "sync",
        {"config_entry_id": entry_id},
        blocking=True,
    )
    request.assert_awaited_with("sync")


async def test_service_unknown_entry_raises(hass):
    await _setup(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "sync",
            {"config_entry_id": "does-not-exist"},
            blocking=True,
        )
