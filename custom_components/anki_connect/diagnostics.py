"""Diagnostics for the Anki integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY
from .coordinator import AnkiConnectConfigEntry, AnkiData

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AnkiConnectConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    # A loaded entry has always had a successful first refresh, but guard
    # against a None snapshot so diagnostics never raises.
    data = coordinator.data or AnkiData()
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "data": {
            "available": data.available,
            "version": data.version,
            "reviewed_today": data.reviewed_today,
            "review_active": data.review_active,
            "deck_count": data.deck_count,
            "cards_due": data.cards_due,
            "new_cards": data.new_cards,
            "learning_cards": data.learning_cards,
            "review_cards": data.review_cards,
            "total_cards": data.total_cards,
            "decks": {
                name: {
                    "deck_id": deck.deck_id,
                    "new": deck.new,
                    "learn": deck.learn,
                    "review": deck.review,
                    "total": deck.total,
                    "due": deck.due,
                }
                for name, deck in data.decks.items()
            },
            "profiles": data.profiles,
            "tag_count": len(data.tags),
            "model_count": len(data.models),
            "media_dir": data.media_dir,
        },
    }
