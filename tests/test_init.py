"""Tests for entry setup and unload."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.api import AnkiConnectError
from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData, DeckStats


def _snapshot() -> AnkiData:
    return AnkiData(
        available=True,
        version=6,
        reviewed_today=3,
        review_active=False,
        decks={"Default": DeckStats(1, "Default", 1, 0, 2, 5)},
    )


async def test_setup_and_unload_entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.anki_connect.coordinator.AnkiDataUpdateCoordinator._async_update_data",
        return_value=_snapshot(),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert hass.services.has_service(DOMAIN, "sync")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_cold_start_with_anki_closed(hass):
    """Setup with Anki closed and no prior data still loads the entry.

    Collection sensors are unavailable and no per-deck sensors are created
    until a successful poll arrives; afterwards they register and populate.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.anki_connect.coordinator."
        "AnkiDataUpdateCoordinator._async_update_data",
        side_effect=AnkiConnectError("Anki closed"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    coordinator = entry.runtime_data
    assert coordinator.data is None

    # Collection sensors exist but are unavailable without a snapshot.
    assert hass.states.get("sensor.anki_cards_due").state == "unavailable"
    # No per-deck sensors registered yet.
    assert hass.states.get("sensor.default_cards_due") is None

    # First successful poll: per-deck sensors register and populate.
    coordinator.async_set_updated_data(_snapshot())
    await hass.async_block_till_done()

    assert hass.states.get("sensor.anki_cards_due").state == "3"
    assert hass.states.get("sensor.default_cards_due").state == "3"
