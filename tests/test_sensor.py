"""Tests for Anki sensors (aggregate, diagnostic, per-deck)."""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData, DeckStats


def _snapshot() -> AnkiData:
    return AnkiData(
        available=True,
        version=6,
        reviewed_today=7,
        review_active=False,
        decks={
            "Default": DeckStats(1, "Default", 2, 1, 3, 10),
            "Spanish": DeckStats(2, "Spanish", 5, 0, 4, 40),
        },
        profiles=["User 1"],
        tags=["a", "b"],
        models=["Basic"],
        media_dir="/media",
    )


async def _setup(hass) -> MockConfigEntry:
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
    return entry


async def test_aggregate_sensors(hass):
    await _setup(hass)
    assert hass.states.get("sensor.anki_cards_reviewed_today").state == "7"
    assert hass.states.get("sensor.anki_cards_due").state == "15"
    assert hass.states.get("sensor.anki_new_cards").state == "7"
    assert hass.states.get("sensor.anki_total_cards").state == "50"
    assert hass.states.get("sensor.anki_decks").state == "2"


async def test_per_deck_sensors_created(hass):
    await _setup(hass)
    # One device + sensors per deck; due = new + learn + review.
    assert hass.states.get("sensor.spanish_cards_due").state == "9"
    assert hass.states.get("sensor.default_total_cards").state == "10"


async def test_per_deck_sensors_added_dynamically(hass):
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    assert hass.states.get("sensor.french_cards_due") is None

    # A new deck appears in a later poll → its sensors are added live.
    snapshot = _snapshot()
    snapshot.decks["French"] = DeckStats(3, "French", 1, 2, 3, 6)
    coordinator.async_set_updated_data(snapshot)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.french_cards_due").state == "6"

    # The same deck in a subsequent poll must NOT re-register duplicates.
    coordinator.async_set_updated_data(snapshot)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.french_cards_due").state == "6"


async def test_entities_keep_last_value_when_anki_closed(hass):
    # Anki goes offline: the snapshot is retained but marked unavailable.
    # Entities must stay available with their last-known values rather than
    # flipping to "unavailable".
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    assert hass.states.get("sensor.anki_cards_due").state == "15"

    coordinator.async_set_updated_data(replace(_snapshot(), available=False))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.anki_cards_due")
    assert state.state == "15"
    assert state.state != "unavailable"
    assert hass.states.get("sensor.spanish_cards_due").state == "9"
