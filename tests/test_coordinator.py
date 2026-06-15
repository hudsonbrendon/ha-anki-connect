"""Tests for the Anki data update coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.anki_connect.api import AnkiConnectError
from custom_components.anki_connect.coordinator import (
    AnkiDataUpdateCoordinator,
    DeckStats,
)


def _deck_stats_payload() -> dict:
    return {
        "1": {"deck_id": 1, "name": "Default", "new_count": 2, "learn_count": 1,
              "review_count": 3, "total_in_deck": 10},
        "2": {"deck_id": 2, "name": "Spanish", "new_count": 5, "learn_count": 0,
              "review_count": 4, "total_in_deck": 40},
    }


def _make_coordinator(hass) -> AnkiDataUpdateCoordinator:
    client = AsyncMock()
    client.async_version.return_value = 6
    client.async_deck_names.return_value = ["Default", "Spanish"]
    client.async_deck_stats.return_value = _deck_stats_payload()
    client.async_num_reviewed_today.return_value = 7
    client.async_review_active.return_value = True
    client.async_tags.return_value = ["tag1", "tag2"]
    client.async_model_names.return_value = ["Basic"]
    client.async_profiles.return_value = ["User 1"]
    client.async_media_dir.return_value = "/media"
    return AnkiDataUpdateCoordinator(
        hass, client=client, name="Anki", scan_interval=60
    )


async def test_deck_stats_due_property():
    deck = DeckStats(deck_id=1, name="Default", new=2, learn=1, review=3, total=10)
    assert deck.due == 6


async def test_update_builds_snapshot(hass):
    coordinator = _make_coordinator(hass)
    data = await coordinator._async_update_data()
    assert data.available is True
    assert data.version == 6
    assert data.reviewed_today == 7
    assert data.review_active is True
    assert set(data.decks) == {"Default", "Spanish"}
    assert data.decks["Spanish"].due == 9
    # Aggregates across decks.
    assert data.new_cards == 7
    assert data.learning_cards == 1
    assert data.review_cards == 7
    assert data.cards_due == 15
    assert data.total_cards == 50
    assert data.deck_count == 2


async def test_update_raises_update_failed_on_error(hass):
    coordinator = _make_coordinator(hass)
    coordinator.client.async_deck_names.side_effect = AnkiConnectError("down")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_update_keeps_last_data_offline_when_anki_closed(hass):
    # First refresh succeeds and seeds coordinator.data.
    coordinator = _make_coordinator(hass)
    first = await coordinator._async_update_data()
    coordinator.data = first
    assert first.available is True

    # Anki is closed on the next poll: return the prior snapshot, marked
    # offline, instead of raising UpdateFailed.
    coordinator.client.async_deck_names.side_effect = AnkiConnectError("closed")
    data = await coordinator._async_update_data()
    assert data.available is False
    # Last-known values are retained.
    assert set(data.decks) == {"Default", "Spanish"}
    assert data.cards_due == 15
    assert data.version == 6


async def test_version_and_static_fields_cached(hass):
    coordinator = _make_coordinator(hass)
    await coordinator._async_update_data()
    await coordinator._async_update_data()
    # version / profiles / media dir fetched once and cached.
    coordinator.client.async_version.assert_called_once()
    coordinator.client.async_profiles.assert_called_once()
    coordinator.client.async_media_dir.assert_called_once()


async def test_static_fields_cached_even_when_version_none(hass):
    # A falsy/None static value must still be cached, not refetched forever.
    coordinator = _make_coordinator(hass)
    coordinator.client.async_version.return_value = None
    await coordinator._async_update_data()
    await coordinator._async_update_data()
    coordinator.client.async_version.assert_called_once()
