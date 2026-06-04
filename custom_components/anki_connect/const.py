"""Constants for the Anki (AnkiConnect) integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "anki_connect"

DEFAULT_NAME: Final = "Anki"
DEFAULT_PORT: Final = 8765
DEFAULT_SCAN_INTERVAL: Final = 60
DEFAULT_TIMEOUT: Final = 10.0

# AnkiConnect JSON-RPC protocol version.
API_VERSION: Final = 6

# Device registry strings.
MANUFACTURER: Final = "Ankitects"

# --- Config / options keys (host, port, name, scan_interval come from homeassistant.const) ---
CONF_API_KEY: Final = "api_key"

# --- AnkiConnect actions used by the coordinator/buttons/services ---
ACTION_VERSION: Final = "version"
ACTION_DECK_NAMES: Final = "deckNames"
ACTION_DECK_STATS: Final = "getDeckStats"
ACTION_REVIEWED_TODAY: Final = "getNumCardsReviewedToday"
ACTION_REVIEWED_BY_DAY: Final = "getNumCardsReviewedByDay"
ACTION_PROFILES: Final = "getProfiles"
ACTION_TAGS: Final = "getTags"
ACTION_MODEL_NAMES: Final = "modelNames"
ACTION_MEDIA_DIR: Final = "getMediaDirPath"
ACTION_REVIEW_ACTIVE: Final = "guiReviewActive"
ACTION_SYNC: Final = "sync"
