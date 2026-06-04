"""Tests for config entry diagnostics."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import CONF_API_KEY, DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData, DeckStats
from custom_components.anki_connect.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_redacts_api_key(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "1.2.3.4",
            CONF_PORT: DEFAULT_PORT,
            CONF_NAME: "Anki",
            CONF_API_KEY: "s3cret",
        },
    )
    entry.add_to_hass(hass)
    snapshot = AnkiData(
        available=True,
        version=6,
        reviewed_today=3,
        decks={"Default": DeckStats(1, "Default", 1, 0, 2, 5)},
    )
    with patch(
        "custom_components.anki_connect.coordinator.AnkiDataUpdateCoordinator._async_update_data",
        return_value=snapshot,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["data"][CONF_API_KEY] == "**REDACTED**"
    # Host is operational info, not a secret — it must NOT be redacted.
    assert diag["entry"]["data"][CONF_HOST] == "1.2.3.4"
    assert diag["data"]["version"] == 6
    assert diag["data"]["deck_count"] == 1
    assert diag["data"]["cards_due"] == 3
    assert diag["data"]["tag_count"] == 0
    assert diag["data"]["model_count"] == 0
    # Per-deck breakdown is present and cross-checks DeckStats.due (1+0+2).
    assert diag["data"]["decks"]["Default"]["due"] == 3
