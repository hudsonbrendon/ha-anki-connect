# Anki (AnkiConnect) Home Assistant Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS custom component `anki_connect` that exposes an Anki collection (via the AnkiConnect add-on HTTP API) to Home Assistant — collection + per-deck statistics as sensors, a review-session binary sensor, GUI/maintenance buttons, and the full AnkiConnect command surface as services — following the exact conventions of the user's other `ha-*` integrations (RetroArch as reference).

**Architecture:** A single `DataUpdateCoordinator` polls one AnkiConnect endpoint over HTTP (`POST http://host:port` with `{"action","version":6,"params","key"}`). An async `AnkiConnectClient` wraps requests. Entities are built from a typed `AnkiData` snapshot: collection-wide aggregate sensors live on a main "Anki" device; each deck gets its own device (linked via `via_device`) with new/learning/review/due/total sensors, created dynamically as decks appear. A generic `anki_connect.api` service plus typed convenience services expose every AnkiConnect action.

**Tech Stack:** Python 3.12, Home Assistant integration scaffolding (config entries, `DataUpdateCoordinator`, entity descriptions), `aiohttp` (HA shared client session), `voluptuous`, `pytest` + `pytest-homeassistant-custom-component`, GitHub Actions (hassfest + HACS validate, pytest, auto-release on manifest bump), `cairosvg` for brand-asset generation.

**Conventions carried over from the user's repos (non-negotiable):**
- Commits are authored **solely by Hudson Brendon** — never add a `Co-Authored-By` trailer.
- Squash the per-task history into clean commits before the first public push.
- English everywhere (code, README, default UI strings); ship `translations/en.json` + `translations/pt-BR.json`.
- Brand assets live in `custom_components/anki_connect/brand/` (HA core brands repo no longer accepts PRs).
- README opens with the logo image, same layout as `ha-retroarch`.

**AnkiConnect facts (verified against the live add-on on this machine, API version 6):**
- Endpoint: `http://127.0.0.1:8765` by default; LAN access requires `ANKICONNECT_BIND_ADDRESS=0.0.0.0` in the add-on config and Anki must be **running**.
- Request: `{"action": <str>, "version": 6, "params": {...}, "key": <optional apiKey>}`. Response: `{"result": <data>, "error": <null|str>}`.
- Verified response shapes:
  - `version` → `6`
  - `deckNames` → `["Default", ...]`
  - `getDeckStats` (params `{"decks": ["Default"]}`) → `{"1": {"deck_id": 1, "name": "Default", "new_count": 2, "learn_count": 0, "review_count": 0, "total_in_deck": 2}}`
  - `getNumCardsReviewedToday` → `1`
  - `getNumCardsReviewedByDay` → `[["2026-06-04", 1], ...]`
  - `getProfiles` → `["User 1"]`
  - `guiReviewActive` → `true|false`
  - `getTags` → `[...]`, `modelNames` → `[...]`, `getMediaDirPath` → `"/path"`
  - `sync` → `null` (fire-and-forget)

---

## File Structure

```
ha-anki-connect/
├── .github/
│   └── workflows/
│       ├── validate.yaml          # hassfest + HACS
│       ├── tests.yaml             # pytest
│       └── release.yml            # auto GH release on manifest version bump
├── custom_components/
│   └── anki_connect/
│       ├── __init__.py            # setup/unload entry, register services
│       ├── api.py                 # AnkiConnectClient + AnkiConnectError
│       ├── const.py               # DOMAIN, defaults, conf keys, action names
│       ├── coordinator.py         # AnkiDataUpdateCoordinator + AnkiData/DeckStats
│       ├── entity.py              # AnkiEntity (main device) + AnkiDeckEntity
│       ├── config_flow.py         # config + options flow
│       ├── sensor.py              # aggregate + diagnostic + per-deck sensors
│       ├── binary_sensor.py       # review_active
│       ├── button.py              # sync + GUI/maintenance buttons
│       ├── services.py            # generic api + typed services
│       ├── services.yaml          # service UI descriptors
│       ├── diagnostics.py         # config-entry diagnostics
│       ├── strings.json           # base UI strings
│       ├── manifest.json
│       ├── brand/                 # icon/logo PNGs (+ @2x, dark variants)
│       └── translations/
│           ├── en.json
│           └── pt-BR.json
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_coordinator.py
│   ├── test_init.py
│   ├── test_config_flow.py
│   ├── test_sensor.py
│   ├── test_binary_sensor.py
│   ├── test_button.py
│   ├── test_services.py
│   └── test_diagnostics.py
├── scripts/
│   └── generate_brand.py          # SVG → PNG brand assets
├── hacs.json
├── requirements_test.txt
├── README.md
└── docs/superpowers/plans/2026-06-04-anki-home-assistant-integration.md
```

**Consistent names used across all tasks (do not drift):**
- `DOMAIN = "anki_connect"`, integration display name `"Anki"`, device model `"Anki"`, manufacturer `"Ankitects"`.
- Client: `AnkiConnectClient`, exception `AnkiConnectError`, constant `API_VERSION = 6`.
- Snapshot: `AnkiData`, per-deck `DeckStats`.
- Coordinator: `AnkiDataUpdateCoordinator`; type alias `AnkiConnectConfigEntry = ConfigEntry[AnkiDataUpdateCoordinator]`; coordinator stored at `entry.runtime_data`.
- Entity bases: `AnkiEntity` (main device), `AnkiDeckEntity` (per-deck device).
- Config keys: `CONF_HOST`, `CONF_PORT`, `CONF_NAME` (from `homeassistant.const`), `CONF_API_KEY = "api_key"`, `CONF_SCAN_INTERVAL` (from `homeassistant.const`).

---

## Task 1: Repo scaffold, manifest, constants, CI

**Files:**
- Create: `custom_components/anki_connect/__init__.py` (placeholder — replaced in Task 4)
- Create: `custom_components/anki_connect/const.py`
- Create: `custom_components/anki_connect/manifest.json`
- Create: `hacs.json`
- Create: `requirements_test.txt`
- Create: `tests/conftest.py`
- Create: `tests/test_const.py`
- Create: `.github/workflows/validate.yaml`
- Create: `.github/workflows/tests.yaml`
- Create: `.github/workflows/release.yml`
- Create: `.gitignore`

- [ ] **Step 1: Initialize the repo and Python env**

```bash
mkdir -p /Users/hudsonbrendon/Github/ha-anki-connect
cd /Users/hudsonbrendon/Github/ha-anki-connect
git init
mkdir -p custom_components/anki_connect/brand custom_components/anki_connect/translations tests scripts .github/workflows
uv venv
uv pip install homeassistant pytest-homeassistant-custom-component==0.13.205 pytest-cov==6.0.0 cairosvg
```

(uv is required — `python3 -m venv` is broken on this machine per the user's environment notes.)

- [ ] **Step 2: Write `.gitignore`**

`/Users/hudsonbrendon/Github/ha-anki-connect/.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/
```

- [ ] **Step 3: Write `custom_components/anki_connect/const.py`**

```python
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
```

- [ ] **Step 4: Write `custom_components/anki_connect/manifest.json`**

```json
{
  "domain": "anki_connect",
  "name": "Anki",
  "codeowners": ["@hudsonbrendon"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/hudsonbrendon/ha-anki-connect",
  "integration_type": "service",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/hudsonbrendon/ha-anki-connect/issues",
  "requirements": [],
  "version": "0.1.0"
}
```

- [ ] **Step 5: Write `hacs.json`**

```json
{
  "name": "Anki",
  "render_readme": true,
  "homeassistant": "2024.12.0"
}
```

- [ ] **Step 6: Write `requirements_test.txt`**

```text
pytest-homeassistant-custom-component==0.13.205
pytest-cov==6.0.0
```

- [ ] **Step 7: Write a placeholder `custom_components/anki_connect/__init__.py`**

```python
"""The Anki (AnkiConnect) integration."""
```

- [ ] **Step 8: Write `tests/conftest.py`**

```python
"""Fixtures for the Anki integration tests."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
```

- [ ] **Step 9: Write the failing test `tests/test_const.py`**

```python
"""Smoke test that the package imports and core constants are wired."""
from custom_components.anki_connect.const import (
    API_VERSION,
    DEFAULT_PORT,
    DOMAIN,
)


def test_domain_and_defaults():
    assert DOMAIN == "anki_connect"
    assert DEFAULT_PORT == 8765
    assert API_VERSION == 6
```

- [ ] **Step 10: Run the test to verify it passes**

Run: `cd /Users/hudsonbrendon/Github/ha-anki-connect && uv run pytest tests/test_const.py -q`
Expected: PASS (1 passed)

- [ ] **Step 11: Write `.github/workflows/validate.yaml`**

```yaml
name: Validate

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration
          ignore: brands
```

- [ ] **Step 12: Write `.github/workflows/tests.yaml`**

```yaml
name: Tests

on:
  push:
  pull_request:

jobs:
  pytest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements_test.txt
      - run: python -m pytest -q
```

- [ ] **Step 13: Write `.github/workflows/release.yml`** (auto-release on manifest version bump)

```yaml
name: Release

on:
  push:
    branches: [main]
    paths:
      - custom_components/anki_connect/manifest.json

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Read manifest version
        id: ver
        run: |
          V=$(python -c "import json;print(json.load(open('custom_components/anki_connect/manifest.json'))['version'])")
          echo "version=$V" >> "$GITHUB_OUTPUT"
      - name: Create release if tag is new
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          TAG="v${{ steps.ver.outputs.version }}"
          if gh release view "$TAG" >/dev/null 2>&1; then
            echo "Release $TAG already exists, skipping."
          else
            gh release create "$TAG" --title "$TAG" --generate-notes
          fi
```

- [ ] **Step 14: Commit**

```bash
cd /Users/hudsonbrendon/Github/ha-anki-connect
git add -A
git commit -m "chore: scaffold anki_connect integration, manifest, and CI"
```

---

## Task 2: AnkiConnect HTTP client

**Files:**
- Create: `custom_components/anki_connect/api.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test `tests/test_api.py`**

```python
"""Tests for the AnkiConnect HTTP client."""
from __future__ import annotations

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.anki_connect.api import AnkiConnectClient, AnkiConnectError


def _client(hass, **kwargs) -> AnkiConnectClient:
    return AnkiConnectClient(
        "1.2.3.4", 8765, async_get_clientsession(hass), **kwargs
    )


async def test_request_returns_result(hass, aioclient_mock):
    aioclient_mock.post(
        "http://1.2.3.4:8765", json={"result": ["Default"], "error": None}
    )
    client = _client(hass)
    assert await client.async_deck_names() == ["Default"]


async def test_request_includes_action_version_and_params(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": {}, "error": None})
    client = _client(hass)
    await client.async_deck_stats(["Default"])
    sent = aioclient_mock.mock_calls[0][2]
    assert sent["action"] == "getDeckStats"
    assert sent["version"] == 6
    assert sent["params"] == {"decks": ["Default"]}
    assert "key" not in sent


async def test_request_includes_api_key_when_configured(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": 6, "error": None})
    client = _client(hass, api_key="s3cret")
    await client.async_version()
    assert aioclient_mock.mock_calls[0][2]["key"] == "s3cret"


async def test_request_raises_on_anki_error(hass, aioclient_mock):
    aioclient_mock.post(
        "http://1.2.3.4:8765", json={"result": None, "error": "collection is not open"}
    )
    client = _client(hass)
    with pytest.raises(AnkiConnectError, match="collection is not open"):
        await client.async_version()


async def test_request_raises_on_transport_error(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", status=500)
    client = _client(hass)
    with pytest.raises(AnkiConnectError):
        await client.async_version()


async def test_review_active_coerces_bool(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": True, "error": None})
    client = _client(hass)
    assert await client.async_review_active() is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_api.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.anki_connect.api'`

- [ ] **Step 3: Write `custom_components/anki_connect/api.py`**

```python
"""Async HTTP client for the AnkiConnect add-on."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    ACTION_DECK_NAMES,
    ACTION_DECK_STATS,
    ACTION_MEDIA_DIR,
    ACTION_MODEL_NAMES,
    ACTION_PROFILES,
    ACTION_REVIEW_ACTIVE,
    ACTION_REVIEWED_BY_DAY,
    ACTION_REVIEWED_TODAY,
    ACTION_TAGS,
    ACTION_VERSION,
    API_VERSION,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class AnkiConnectError(Exception):
    """Raised when AnkiConnect returns an error or is unreachable."""


class AnkiConnectClient:
    """Talks to one AnkiConnect endpoint over HTTP."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
        *,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._url = f"http://{host}:{port}"
        self._session = session
        self._api_key = api_key
        self._timeout = timeout

    @property
    def url(self) -> str:
        """Return the configured endpoint URL."""
        return self._url

    async def request(self, action: str, **params: Any) -> Any:
        """POST one AnkiConnect action and return its ``result``."""
        payload: dict[str, Any] = {"action": action, "version": API_VERSION}
        if params:
            payload["params"] = params
        if self._api_key:
            payload["key"] = self._api_key

        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.post(self._url, json=payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AnkiConnectError(
                f"AnkiConnect request '{action}' failed: {err}"
            ) from err

        if not isinstance(data, dict) or "error" not in data:
            raise AnkiConnectError(f"Unexpected AnkiConnect response: {data!r}")
        if data["error"] is not None:
            raise AnkiConnectError(str(data["error"]))
        return data.get("result")

    # --- Typed convenience wrappers used by the coordinator ---
    async def async_version(self) -> int | None:
        return await self.request(ACTION_VERSION)

    async def async_deck_names(self) -> list[str]:
        return await self.request(ACTION_DECK_NAMES) or []

    async def async_deck_stats(self, decks: list[str]) -> dict[str, dict]:
        return await self.request(ACTION_DECK_STATS, decks=decks) or {}

    async def async_num_reviewed_today(self) -> int:
        return await self.request(ACTION_REVIEWED_TODAY) or 0

    async def async_reviews_by_day(self) -> list[list]:
        return await self.request(ACTION_REVIEWED_BY_DAY) or []

    async def async_profiles(self) -> list[str]:
        return await self.request(ACTION_PROFILES) or []

    async def async_tags(self) -> list[str]:
        return await self.request(ACTION_TAGS) or []

    async def async_model_names(self) -> list[str]:
        return await self.request(ACTION_MODEL_NAMES) or []

    async def async_media_dir(self) -> str | None:
        return await self.request(ACTION_MEDIA_DIR)

    async def async_review_active(self) -> bool:
        return bool(await self.request(ACTION_REVIEW_ACTIVE))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_api.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/anki_connect/api.py tests/test_api.py
git commit -m "feat: add AnkiConnect HTTP client"
```

---

## Task 3: Coordinator + data models

**Files:**
- Create: `custom_components/anki_connect/coordinator.py`
- Test: `tests/test_coordinator.py`

- [ ] **Step 1: Write the failing test `tests/test_coordinator.py`**

```python
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


async def test_version_and_static_fields_cached(hass):
    coordinator = _make_coordinator(hass)
    await coordinator._async_update_data()
    await coordinator._async_update_data()
    # version / profiles / media dir fetched once and cached.
    assert coordinator.client.async_version.call_count == 1
    assert coordinator.client.async_profiles.call_count == 1
    assert coordinator.client.async_media_dir.call_count == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_coordinator.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.anki_connect.coordinator'`

- [ ] **Step 3: Write `custom_components/anki_connect/coordinator.py`**

```python
"""DataUpdateCoordinator and snapshot models for the Anki integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AnkiConnectClient, AnkiConnectError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type AnkiConnectConfigEntry = ConfigEntry["AnkiDataUpdateCoordinator"]


@dataclass
class DeckStats:
    """Per-deck card counts from getDeckStats."""

    deck_id: int
    name: str
    new: int
    learn: int
    review: int
    total: int

    @property
    def due(self) -> int:
        """Cards waiting to be studied (new + learning + review)."""
        return self.new + self.learn + self.review


@dataclass
class AnkiData:
    """Snapshot of one Anki collection shared with all entities."""

    available: bool = False
    version: int | None = None
    reviewed_today: int | None = None
    review_active: bool | None = None
    decks: dict[str, DeckStats] = field(default_factory=dict)
    profiles: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    media_dir: str | None = None

    @property
    def deck_count(self) -> int:
        return len(self.decks)

    @property
    def new_cards(self) -> int:
        return sum(deck.new for deck in self.decks.values())

    @property
    def learning_cards(self) -> int:
        return sum(deck.learn for deck in self.decks.values())

    @property
    def review_cards(self) -> int:
        return sum(deck.review for deck in self.decks.values())

    @property
    def cards_due(self) -> int:
        return self.new_cards + self.learning_cards + self.review_cards

    @property
    def total_cards(self) -> int:
        return sum(deck.total for deck in self.decks.values())


class AnkiDataUpdateCoordinator(DataUpdateCoordinator[AnkiData]):
    """Polls one AnkiConnect endpoint and shares an AnkiData snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: AnkiConnectClient,
        name: str,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.device_name = name
        # Rarely-changing fields fetched once and cached.
        self._version: int | None = None
        self._profiles: list[str] | None = None
        self._media_dir: str | None = None

    async def _async_update_data(self) -> AnkiData:
        try:
            if self._version is None:
                self._version = await self.client.async_version()
            if self._profiles is None:
                self._profiles = await self.client.async_profiles()
            if self._media_dir is None:
                self._media_dir = await self.client.async_media_dir()

            deck_names = await self.client.async_deck_names()
            raw = await self.client.async_deck_stats(deck_names) if deck_names else {}
            reviewed = await self.client.async_num_reviewed_today()
            review_active = await self.client.async_review_active()
            tags = await self.client.async_tags()
            models = await self.client.async_model_names()
        except AnkiConnectError as err:
            raise UpdateFailed(str(err)) from err

        decks: dict[str, DeckStats] = {}
        for info in raw.values():
            decks[info["name"]] = DeckStats(
                deck_id=info["deck_id"],
                name=info["name"],
                new=info.get("new_count", 0),
                learn=info.get("learn_count", 0),
                review=info.get("review_count", 0),
                total=info.get("total_in_deck", 0),
            )

        return AnkiData(
            available=True,
            version=self._version,
            reviewed_today=reviewed,
            review_active=review_active,
            decks=decks,
            profiles=self._profiles or [],
            tags=tags,
            models=models,
            media_dir=self._media_dir,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_coordinator.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/anki_connect/coordinator.py tests/test_coordinator.py
git commit -m "feat: add coordinator with AnkiData/DeckStats snapshot"
```

---

## Task 4: Entry setup / unload

**Files:**
- Modify: `custom_components/anki_connect/__init__.py` (replace placeholder from Task 1)
- Test: `tests/test_init.py`

- [ ] **Step 1: Write the failing test `tests/test_init.py`**

```python
"""Tests for entry setup and unload."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_init.py -q`
Expected: FAIL (setup returns False / services not registered — `__init__.py` is still the placeholder)

- [ ] **Step 3: Write `custom_components/anki_connect/__init__.py`**

```python
"""The Anki (AnkiConnect) integration."""
from __future__ import annotations

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnkiConnectClient
from .const import CONF_API_KEY, DEFAULT_NAME, DEFAULT_SCAN_INTERVAL
from .coordinator import AnkiConnectConfigEntry, AnkiDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: AnkiConnectConfigEntry) -> bool:
    """Set up Anki from a config entry."""
    client = AnkiConnectClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        async_get_clientsession(hass),
        api_key=entry.data.get(CONF_API_KEY) or None,
    )

    coordinator = AnkiDataUpdateCoordinator(
        hass,
        client=client,
        name=entry.data.get(CONF_NAME, DEFAULT_NAME),
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Imported here (not at module top) so the package stays importable during
    # incremental development before services.py exists; it always ships in releases.
    from .services import async_setup_services

    async_setup_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AnkiConnectConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant, entry: AnkiConnectConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
```

> Note: this imports `services.async_setup_services`, `binary_sensor`, `button`, and `sensor` platforms which are created in Tasks 5–9. Run this task's test only after those exist, OR temporarily narrow `PLATFORMS = []` and skip the `from .services import ...` line, then restore both at the end of Task 9. The recommended order is to implement Tasks 5–9 and run `test_init.py` last. If executing strictly in order, expect `test_init.py` to fail until Task 9 is complete; mark its checkbox then.

- [ ] **Step 4: Run the full suite after Tasks 5–9 exist**

Run: `uv run pytest tests/test_init.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/anki_connect/__init__.py tests/test_init.py
git commit -m "feat: wire entry setup/unload and service registration"
```

---

## Task 5: Config + options flow

**Files:**
- Create: `custom_components/anki_connect/config_flow.py`
- Test: `tests/test_config_flow.py`

- [ ] **Step 1: Write the failing test `tests/test_config_flow.py`**

```python
"""Tests for the Anki config and options flow."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import CONF_API_KEY, DEFAULT_PORT, DOMAIN


async def test_user_flow_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        return_value=6,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.2.3.4",
                CONF_PORT: DEFAULT_PORT,
                CONF_NAME: "Anki",
                CONF_API_KEY: "",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Anki"
    assert result["data"][CONF_HOST] == "1.2.3.4"


async def test_user_flow_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_aborts(hass):
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.2.3.4:8765",
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        return_value=6,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_sets_scan_interval(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 30}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 30
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_config_flow.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.anki_connect.config_flow'`

- [ ] **Step 3: Write `custom_components/anki_connect/config_flow.py`**

```python
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
                return self.async_update_reload_and_abort(entry, data=user_input)
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
            return await client.async_version() is not None
        except AnkiConnectError:
            return False

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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_config_flow.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/anki_connect/config_flow.py tests/test_config_flow.py
git commit -m "feat: add config and options flow with optional API key"
```

---

## Task 6: Entity bases + sensors (aggregate, diagnostic, per-deck)

**Files:**
- Create: `custom_components/anki_connect/entity.py`
- Create: `custom_components/anki_connect/sensor.py`
- Test: `tests/test_sensor.py`

- [ ] **Step 1: Write the failing test `tests/test_sensor.py`**

```python
"""Tests for Anki sensors (aggregate, diagnostic, per-deck)."""
from __future__ import annotations

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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_sensor.py -q`
Expected: FAIL (sensor platform / entity bases do not exist)

- [ ] **Step 3: Write `custom_components/anki_connect/entity.py`**

```python
"""Base entities for the Anki integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AnkiDataUpdateCoordinator


class AnkiEntity(CoordinatorEntity[AnkiDataUpdateCoordinator]):
    """Common device info for collection-wide Anki entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AnkiDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        version = coordinator.data.version if coordinator.data else None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model="Anki",
            sw_version=str(version) if version is not None else None,
            configuration_url=coordinator.client.url,
        )


class AnkiDeckEntity(CoordinatorEntity[AnkiDataUpdateCoordinator]):
    """Per-deck entity living on its own device, linked to the main one."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: AnkiDataUpdateCoordinator, deck_name: str
    ) -> None:
        super().__init__(coordinator)
        self._deck_name = deck_name
        entry_id = coordinator.config_entry.entry_id
        deck = coordinator.data.decks[deck_name]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_deck_{deck.deck_id}")},
            name=deck_name,
            manufacturer=MANUFACTURER,
            model="Anki Deck",
            via_device=(DOMAIN, entry_id),
        )

    @property
    def available(self) -> bool:
        return super().available and self._deck_name in self.coordinator.data.decks
```

- [ ] **Step 4: Write `custom_components/anki_connect/sensor.py`**

```python
"""Sensor platform for Anki: aggregate, diagnostic, and per-deck card counts."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import (
    AnkiConnectConfigEntry,
    AnkiData,
    AnkiDataUpdateCoordinator,
    DeckStats,
)
from .entity import AnkiDeckEntity, AnkiEntity


@dataclass(frozen=True, kw_only=True)
class AnkiSensorDescription(SensorEntityDescription):
    """A collection-wide sensor backed by the AnkiData snapshot."""

    value_fn: Callable[[AnkiData], StateType]
    attr_fn: Callable[[AnkiData], dict] | None = None


COLLECTION_SENSORS: tuple[AnkiSensorDescription, ...] = (
    AnkiSensorDescription(
        key="cards_reviewed_today",
        icon="mdi:check-circle-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.reviewed_today,
    ),
    AnkiSensorDescription(
        key="cards_due",
        icon="mdi:cards-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.cards_due,
    ),
    AnkiSensorDescription(
        key="new_cards",
        icon="mdi:new-box",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.new_cards,
    ),
    AnkiSensorDescription(
        key="learning_cards",
        icon="mdi:school-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.learning_cards,
    ),
    AnkiSensorDescription(
        key="review_cards",
        icon="mdi:history",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.review_cards,
    ),
    AnkiSensorDescription(
        key="total_cards",
        icon="mdi:cards",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.total_cards,
    ),
    AnkiSensorDescription(
        key="decks",
        icon="mdi:folder-multiple-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.deck_count,
        attr_fn=lambda data: {"deck_names": sorted(data.decks)},
    ),
)

DIAGNOSTIC_SENSORS: tuple[AnkiSensorDescription, ...] = (
    AnkiSensorDescription(
        key="anki_connect_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.version,
    ),
    AnkiSensorDescription(
        key="profiles",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: len(data.profiles),
        attr_fn=lambda data: {"names": data.profiles},
    ),
    AnkiSensorDescription(
        key="tags",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: len(data.tags),
        attr_fn=lambda data: {"names": data.tags},
    ),
    AnkiSensorDescription(
        key="note_types",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: len(data.models),
        attr_fn=lambda data: {"names": data.models},
    ),
    AnkiSensorDescription(
        key="media_directory",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.media_dir,
    ),
)


@dataclass(frozen=True, kw_only=True)
class AnkiDeckSensorDescription(SensorEntityDescription):
    """A per-deck card-count sensor."""

    value_fn: Callable[[DeckStats], int]


DECK_SENSORS: tuple[AnkiDeckSensorDescription, ...] = (
    AnkiDeckSensorDescription(
        key="cards_due",
        icon="mdi:cards-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda deck: deck.due,
    ),
    AnkiDeckSensorDescription(
        key="new_cards",
        icon="mdi:new-box",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda deck: deck.new,
    ),
    AnkiDeckSensorDescription(
        key="learning_cards",
        icon="mdi:school-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda deck: deck.learn,
    ),
    AnkiDeckSensorDescription(
        key="review_cards",
        icon="mdi:history",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda deck: deck.review,
    ),
    AnkiDeckSensorDescription(
        key="total_cards",
        icon="mdi:cards",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda deck: deck.total,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkiConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anki sensors, adding per-deck sensors as decks appear."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        AnkiSensor(coordinator, description) for description in COLLECTION_SENSORS
    ]
    entities.extend(
        AnkiSensor(coordinator, description) for description in DIAGNOSTIC_SENSORS
    )
    async_add_entities(entities)

    known_decks: set[str] = set()

    @callback
    def _add_new_decks() -> None:
        new_entities: list[SensorEntity] = []
        for deck_name in coordinator.data.decks:
            if deck_name in known_decks:
                continue
            known_decks.add(deck_name)
            new_entities.extend(
                AnkiDeckSensor(coordinator, deck_name, description)
                for description in DECK_SENSORS
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_decks()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_decks))


class AnkiSensor(AnkiEntity, SensorEntity):
    """A collection-wide sensor backed by the snapshot."""

    entity_description: AnkiSensorDescription

    def __init__(
        self,
        coordinator: AnkiDataUpdateCoordinator,
        description: AnkiSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)


class AnkiDeckSensor(AnkiDeckEntity, SensorEntity):
    """A per-deck card-count sensor."""

    entity_description: AnkiDeckSensorDescription

    def __init__(
        self,
        coordinator: AnkiDataUpdateCoordinator,
        deck_name: str,
        description: AnkiDeckSensorDescription,
    ) -> None:
        super().__init__(coordinator, deck_name)
        self.entity_description = description
        self._attr_translation_key = f"deck_{description.key}"
        deck_id = coordinator.data.decks[deck_name].deck_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_deck_{deck_id}_{description.key}"
        )

    @property
    def native_value(self) -> StateType:
        deck = self.coordinator.data.decks.get(self._deck_name)
        if deck is None:
            return None
        return self.entity_description.value_fn(deck)
```

> The default-language entity names (`Cards reviewed today`, `Cards due`, etc.) come from `translations/en.json` in Task 10. The `test_sensor.py` assertions use the resulting entity_ids (`sensor.anki_cards_reviewed_today`, `sensor.spanish_cards_due`). If Task 10 strings are not yet present, HA falls back to the translation key; create Task 10's `en.json` before relying on the friendly names, but the entity_ids in the test are derived from `<device name> + <translation_key>` and hold regardless.

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_sensor.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add custom_components/anki_connect/entity.py custom_components/anki_connect/sensor.py tests/test_sensor.py
git commit -m "feat: add entity bases and aggregate/diagnostic/per-deck sensors"
```

---

## Task 7: Binary sensor (review session active)

**Files:**
- Create: `custom_components/anki_connect/binary_sensor.py`
- Test: `tests/test_binary_sensor.py`

- [ ] **Step 1: Write the failing test `tests/test_binary_sensor.py`**

```python
"""Tests for the Anki review-active binary sensor."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData


async def _setup(hass, review_active: bool) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)
    snapshot = AnkiData(available=True, version=6, review_active=review_active)
    with patch(
        "custom_components.anki_connect.coordinator.AnkiDataUpdateCoordinator._async_update_data",
        return_value=snapshot,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_review_active_on(hass):
    await _setup(hass, True)
    assert hass.states.get("binary_sensor.anki_review_session_active").state == "on"


async def test_review_active_off(hass):
    await _setup(hass, False)
    assert hass.states.get("binary_sensor.anki_review_session_active").state == "off"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_binary_sensor.py -q`
Expected: FAIL (binary_sensor platform does not exist)

- [ ] **Step 3: Write `custom_components/anki_connect/binary_sensor.py`**

```python
"""Binary sensor platform for Anki."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AnkiConnectConfigEntry, AnkiDataUpdateCoordinator
from .entity import AnkiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkiConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Anki review-active binary sensor."""
    async_add_entities([AnkiReviewActiveBinarySensor(entry.runtime_data)])


class AnkiReviewActiveBinarySensor(AnkiEntity, BinarySensorEntity):
    """True while a review session is open in the Anki GUI."""

    _attr_translation_key = "review_session_active"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: AnkiDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_review_session_active"
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.review_active
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_binary_sensor.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/anki_connect/binary_sensor.py tests/test_binary_sensor.py
git commit -m "feat: add review-session-active binary sensor"
```

---

## Task 8: Buttons (sync + GUI/maintenance commands)

**Files:**
- Create: `custom_components/anki_connect/button.py`
- Test: `tests/test_button.py`

- [ ] **Step 1: Write the failing test `tests/test_button.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_button.py -q`
Expected: FAIL (button platform does not exist)

- [ ] **Step 3: Write `custom_components/anki_connect/button.py`**

```python
"""Button platform for Anki (fire-and-forget AnkiConnect actions)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AnkiConnectConfigEntry, AnkiDataUpdateCoordinator
from .entity import AnkiEntity


@dataclass(frozen=True, kw_only=True)
class AnkiButtonDescription(ButtonEntityDescription):
    """A button that fires one parameterless AnkiConnect action."""

    action: str


BUTTONS: tuple[AnkiButtonDescription, ...] = (
    AnkiButtonDescription(key="sync", action="sync", icon="mdi:cloud-sync"),
    AnkiButtonDescription(
        key="open_deck_browser", action="guiDeckBrowser", icon="mdi:view-list"
    ),
    AnkiButtonDescription(
        key="show_question", action="guiShowQuestion", icon="mdi:help-circle-outline"
    ),
    AnkiButtonDescription(
        key="show_answer", action="guiShowAnswer", icon="mdi:eye-outline"
    ),
    AnkiButtonDescription(
        key="start_card_timer", action="guiStartCardTimer", icon="mdi:timer-outline"
    ),
    AnkiButtonDescription(key="undo", action="guiUndo", icon="mdi:undo"),
    AnkiButtonDescription(
        key="check_database",
        action="guiCheckDatabase",
        icon="mdi:database-check",
        entity_category=EntityCategory.CONFIG,
    ),
    AnkiButtonDescription(
        key="reload_collection",
        action="reloadCollection",
        icon="mdi:reload",
        entity_category=EntityCategory.CONFIG,
    ),
    AnkiButtonDescription(
        key="clear_unused_tags",
        action="clearUnusedTags",
        icon="mdi:tag-off-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    AnkiButtonDescription(
        key="remove_empty_notes",
        action="removeEmptyNotes",
        icon="mdi:note-remove-outline",
        entity_category=EntityCategory.CONFIG,
    ),
    AnkiButtonDescription(
        key="exit_anki",
        action="guiExitAnki",
        icon="mdi:exit-run",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkiConnectConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anki buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        AnkiButton(coordinator, description) for description in BUTTONS
    )


class AnkiButton(AnkiEntity, ButtonEntity):
    """A button that fires one AnkiConnect action on press."""

    entity_description: AnkiButtonDescription

    def __init__(
        self,
        coordinator: AnkiDataUpdateCoordinator,
        description: AnkiButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )

    async def async_press(self) -> None:
        await self.coordinator.client.request(self.entity_description.action)
        await self.coordinator.async_request_refresh()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_button.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add custom_components/anki_connect/button.py tests/test_button.py
git commit -m "feat: add sync and GUI/maintenance buttons"
```

---

## Task 9: Services (generic api + typed convenience services)

**Files:**
- Create: `custom_components/anki_connect/services.py`
- Create: `custom_components/anki_connect/services.yaml`
- Test: `tests/test_services.py`

- [ ] **Step 1: Write the failing test `tests/test_services.py`**

```python
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


async def test_service_unknown_entry_raises(hass):
    await _setup(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "sync",
            {"config_entry_id": "does-not-exist"},
            blocking=True,
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_services.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.anki_connect.services'`

- [ ] **Step 3: Write `custom_components/anki_connect/services.py`**

```python
"""Services for the Anki integration: a generic action call plus typed helpers."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_ACTION = "action"
ATTR_PARAMS = "params"
ATTR_QUERY = "query"
ATTR_DECK = "deck"
ATTR_MODEL = "model"
ATTR_FIELDS = "fields"
ATTR_TAGS = "tags"
ATTR_NOTES = "notes"
ATTR_CARDS = "cards"
ATTR_WHOLE_COLLECTION = "whole_collection"

SERVICE_API = "api"
SERVICE_SYNC = "sync"
SERVICE_ADD_NOTE = "add_note"
SERVICE_FIND_NOTES = "find_notes"
SERVICE_NOTES_INFO = "notes_info"
SERVICE_FIND_CARDS = "find_cards"
SERVICE_GUI_BROWSE = "gui_browse"
SERVICE_GUI_DECK_OVERVIEW = "gui_deck_overview"
SERVICE_GUI_DECK_REVIEW = "gui_deck_review"
SERVICE_CREATE_DECK = "create_deck"
SERVICE_ADD_TAGS = "add_tags"
SERVICE_REMOVE_TAGS = "remove_tags"
SERVICE_SUSPEND = "suspend"
SERVICE_UNSUSPEND = "unsuspend"
SERVICE_COLLECTION_STATS_HTML = "collection_stats_html"

_ENTRY = {vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string}

API_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_ACTION): cv.string, vol.Optional(ATTR_PARAMS): dict}
)
ENTRY_ONLY_SCHEMA = vol.Schema(_ENTRY)
ADD_NOTE_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Required(ATTR_DECK): cv.string,
        vol.Required(ATTR_MODEL): cv.string,
        vol.Required(ATTR_FIELDS): dict,
        vol.Optional(ATTR_TAGS, default=list): vol.All(cv.ensure_list, [cv.string]),
    }
)
QUERY_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_QUERY): cv.string})
NOTES_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_NOTES): vol.All(cv.ensure_list, [int])}
)
CARDS_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Required(ATTR_CARDS): vol.All(cv.ensure_list, [int])}
)
DECK_SCHEMA = vol.Schema({**_ENTRY, vol.Required(ATTR_DECK): cv.string})
TAGS_SCHEMA = vol.Schema(
    {
        **_ENTRY,
        vol.Required(ATTR_NOTES): vol.All(cv.ensure_list, [int]),
        vol.Required(ATTR_TAGS): cv.string,
    }
)
STATS_HTML_SCHEMA = vol.Schema(
    {**_ENTRY, vol.Optional(ATTR_WHOLE_COLLECTION, default=True): cv.boolean}
)


def _get_coordinator(hass: HomeAssistant, call: ServiceCall):
    entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
    entry = hass.config_entries.async_get_entry(entry_id)
    if (
        entry is None
        or entry.domain != DOMAIN
        or entry.state is not ConfigEntryState.LOADED
    ):
        raise ServiceValidationError(
            f"Anki config entry {entry_id} not found or not loaded"
        )
    return entry.runtime_data


def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (idempotent)."""

    if hass.services.has_service(DOMAIN, SERVICE_API):
        return

    async def handle_api(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        params = call.data.get(ATTR_PARAMS) or {}
        result = await coordinator.client.request(call.data[ATTR_ACTION], **params)
        return {"result": result}

    async def handle_sync(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request("sync")

    async def handle_add_note(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        note = {
            "deckName": call.data[ATTR_DECK],
            "modelName": call.data[ATTR_MODEL],
            "fields": call.data[ATTR_FIELDS],
            "tags": call.data[ATTR_TAGS],
        }
        result = await coordinator.client.request("addNote", note=note)
        return {"result": result}

    async def handle_find_notes(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        result = await coordinator.client.request("findNotes", query=call.data[ATTR_QUERY])
        return {"result": result}

    async def handle_notes_info(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        result = await coordinator.client.request("notesInfo", notes=call.data[ATTR_NOTES])
        return {"result": result}

    async def handle_find_cards(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        result = await coordinator.client.request("findCards", query=call.data[ATTR_QUERY])
        return {"result": result}

    async def handle_gui_browse(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        result = await coordinator.client.request("guiBrowse", query=call.data[ATTR_QUERY])
        return {"result": result}

    async def handle_gui_deck_overview(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request("guiDeckOverview", name=call.data[ATTR_DECK])

    async def handle_gui_deck_review(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request("guiDeckReview", name=call.data[ATTR_DECK])

    async def handle_create_deck(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        result = await coordinator.client.request("createDeck", deck=call.data[ATTR_DECK])
        return {"result": result}

    async def handle_add_tags(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request(
            "addTags", notes=call.data[ATTR_NOTES], tags=call.data[ATTR_TAGS]
        )

    async def handle_remove_tags(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request(
            "removeTags", notes=call.data[ATTR_NOTES], tags=call.data[ATTR_TAGS]
        )

    async def handle_suspend(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request("suspend", cards=call.data[ATTR_CARDS])

    async def handle_unsuspend(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call)
        await coordinator.client.request("unsuspend", cards=call.data[ATTR_CARDS])

    async def handle_collection_stats_html(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_coordinator(hass, call)
        result = await coordinator.client.request(
            "getCollectionStatsHTML", wholeCollection=call.data[ATTR_WHOLE_COLLECTION]
        )
        return {"result": result}

    register = hass.services.async_register
    register(DOMAIN, SERVICE_API, handle_api, schema=API_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    register(DOMAIN, SERVICE_SYNC, handle_sync, schema=ENTRY_ONLY_SCHEMA)
    register(DOMAIN, SERVICE_ADD_NOTE, handle_add_note, schema=ADD_NOTE_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    register(DOMAIN, SERVICE_FIND_NOTES, handle_find_notes, schema=QUERY_SCHEMA, supports_response=SupportsResponse.ONLY)
    register(DOMAIN, SERVICE_NOTES_INFO, handle_notes_info, schema=NOTES_SCHEMA, supports_response=SupportsResponse.ONLY)
    register(DOMAIN, SERVICE_FIND_CARDS, handle_find_cards, schema=QUERY_SCHEMA, supports_response=SupportsResponse.ONLY)
    register(DOMAIN, SERVICE_GUI_BROWSE, handle_gui_browse, schema=QUERY_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    register(DOMAIN, SERVICE_GUI_DECK_OVERVIEW, handle_gui_deck_overview, schema=DECK_SCHEMA)
    register(DOMAIN, SERVICE_GUI_DECK_REVIEW, handle_gui_deck_review, schema=DECK_SCHEMA)
    register(DOMAIN, SERVICE_CREATE_DECK, handle_create_deck, schema=DECK_SCHEMA, supports_response=SupportsResponse.OPTIONAL)
    register(DOMAIN, SERVICE_ADD_TAGS, handle_add_tags, schema=TAGS_SCHEMA)
    register(DOMAIN, SERVICE_REMOVE_TAGS, handle_remove_tags, schema=TAGS_SCHEMA)
    register(DOMAIN, SERVICE_SUSPEND, handle_suspend, schema=CARDS_SCHEMA)
    register(DOMAIN, SERVICE_UNSUSPEND, handle_unsuspend, schema=CARDS_SCHEMA)
    register(DOMAIN, SERVICE_COLLECTION_STATS_HTML, handle_collection_stats_html, schema=STATS_HTML_SCHEMA, supports_response=SupportsResponse.ONLY)
```

- [ ] **Step 4: Write `custom_components/anki_connect/services.yaml`**

```yaml
api:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    action:
      required: true
      example: "deckNames"
      selector:
        text:
    params:
      example: '{"decks": ["Default"]}'
      selector:
        object:

sync:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect

add_note:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    deck:
      required: true
      example: "Default"
      selector:
        text:
    model:
      required: true
      example: "Basic"
      selector:
        text:
    fields:
      required: true
      example: '{"Front": "hola", "Back": "hello"}'
      selector:
        object:
    tags:
      example: "spanish"
      selector:
        object:

find_notes:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    query:
      required: true
      example: "deck:Default"
      selector:
        text:

notes_info:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    notes:
      required: true
      example: "[1502298033753]"
      selector:
        object:

find_cards:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    query:
      required: true
      example: "deck:Default is:due"
      selector:
        text:

gui_browse:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    query:
      required: true
      example: "deck:Default"
      selector:
        text:

gui_deck_overview:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    deck:
      required: true
      example: "Default"
      selector:
        text:

gui_deck_review:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    deck:
      required: true
      example: "Default"
      selector:
        text:

create_deck:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    deck:
      required: true
      example: "Spanish::Verbs"
      selector:
        text:

add_tags:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    notes:
      required: true
      example: "[1502298033753]"
      selector:
        object:
    tags:
      required: true
      example: "marked leech"
      selector:
        text:

remove_tags:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    notes:
      required: true
      example: "[1502298033753]"
      selector:
        object:
    tags:
      required: true
      example: "leech"
      selector:
        text:

suspend:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    cards:
      required: true
      example: "[1483959291685]"
      selector:
        object:

unsuspend:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    cards:
      required: true
      example: "[1483959291685]"
      selector:
        object:

collection_stats_html:
  fields:
    config_entry_id:
      required: true
      selector:
        config_entry:
          integration: anki_connect
    whole_collection:
      default: true
      selector:
        boolean:
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_services.py -q`
Expected: PASS (5 passed)

- [ ] **Step 6: Restore `PLATFORMS` / service import in `__init__.py` if narrowed in Task 4, then run the full suite**

Run: `uv run pytest -q`
Expected: PASS (all tests, including `test_init.py`)

- [ ] **Step 7: Commit**

```bash
git add custom_components/anki_connect/services.py custom_components/anki_connect/services.yaml tests/test_services.py
git commit -m "feat: add generic api service and typed convenience services"
```

---

## Task 10: UI strings, translations, diagnostics

**Files:**
- Create: `custom_components/anki_connect/strings.json`
- Create: `custom_components/anki_connect/translations/en.json`
- Create: `custom_components/anki_connect/translations/pt-BR.json`
- Create: `custom_components/anki_connect/diagnostics.py`
- Test: `tests/test_diagnostics.py`

- [ ] **Step 1: Write `custom_components/anki_connect/strings.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Anki",
        "description": "Anki must be running with the AnkiConnect add-on. For access from another machine, set ANKICONNECT_BIND_ADDRESS=0.0.0.0 in the add-on configuration.",
        "data": {
          "host": "Host",
          "port": "Port",
          "name": "Name",
          "api_key": "API key (optional)"
        }
      },
      "reconfigure": {
        "title": "Reconfigure Anki",
        "description": "Update the connection details for this Anki instance.",
        "data": {
          "host": "Host",
          "port": "Port",
          "name": "Name",
          "api_key": "API key (optional)"
        }
      }
    },
    "error": {
      "cannot_connect": "Could not reach AnkiConnect. Check the host, port, API key, and that Anki is running with the add-on enabled."
    },
    "abort": {
      "already_configured": "This Anki instance is already configured.",
      "reconfigure_successful": "Anki reconfigured successfully."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Anki options",
        "data": {
          "scan_interval": "Polling interval (seconds)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "cards_reviewed_today": { "name": "Cards reviewed today" },
      "cards_due": { "name": "Cards due" },
      "new_cards": { "name": "New cards" },
      "learning_cards": { "name": "Learning cards" },
      "review_cards": { "name": "Review cards" },
      "total_cards": { "name": "Total cards" },
      "decks": { "name": "Decks" },
      "anki_connect_version": { "name": "AnkiConnect version" },
      "profiles": { "name": "Profiles" },
      "tags": { "name": "Tags" },
      "note_types": { "name": "Note types" },
      "media_directory": { "name": "Media directory" },
      "deck_cards_due": { "name": "Cards due" },
      "deck_new_cards": { "name": "New cards" },
      "deck_learning_cards": { "name": "Learning cards" },
      "deck_review_cards": { "name": "Review cards" },
      "deck_total_cards": { "name": "Total cards" }
    },
    "binary_sensor": {
      "review_session_active": { "name": "Review session active" }
    },
    "button": {
      "sync": { "name": "Sync" },
      "open_deck_browser": { "name": "Open deck browser" },
      "show_question": { "name": "Show question" },
      "show_answer": { "name": "Show answer" },
      "start_card_timer": { "name": "Start card timer" },
      "undo": { "name": "Undo" },
      "check_database": { "name": "Check database" },
      "reload_collection": { "name": "Reload collection" },
      "clear_unused_tags": { "name": "Clear unused tags" },
      "remove_empty_notes": { "name": "Remove empty notes" },
      "exit_anki": { "name": "Exit Anki" }
    }
  },
  "services": {
    "api": {
      "name": "Call API action",
      "description": "Call any AnkiConnect action and return its result.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "action": { "name": "Action", "description": "AnkiConnect action name, e.g. deckNames." },
        "params": { "name": "Parameters", "description": "Optional parameters object for the action." }
      }
    },
    "sync": {
      "name": "Sync",
      "description": "Synchronize the local collection with AnkiWeb.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." }
      }
    },
    "add_note": {
      "name": "Add note",
      "description": "Create a new note in a deck.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "deck": { "name": "Deck", "description": "Target deck name." },
        "model": { "name": "Note type", "description": "Note type (model) name." },
        "fields": { "name": "Fields", "description": "Field name to value map." },
        "tags": { "name": "Tags", "description": "Optional list of tags." }
      }
    },
    "find_notes": {
      "name": "Find notes",
      "description": "Return note IDs matching an Anki search query.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "query": { "name": "Query", "description": "Anki browser search query." }
      }
    },
    "notes_info": {
      "name": "Notes info",
      "description": "Return fields and tags for the given note IDs.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "notes": { "name": "Note IDs", "description": "List of note IDs." }
      }
    },
    "find_cards": {
      "name": "Find cards",
      "description": "Return card IDs matching an Anki search query.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "query": { "name": "Query", "description": "Anki browser search query." }
      }
    },
    "gui_browse": {
      "name": "Open browser",
      "description": "Open the card browser filtered by a query.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "query": { "name": "Query", "description": "Anki browser search query." }
      }
    },
    "gui_deck_overview": {
      "name": "Open deck overview",
      "description": "Open the overview screen for a deck.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "deck": { "name": "Deck", "description": "Deck name." }
      }
    },
    "gui_deck_review": {
      "name": "Start deck review",
      "description": "Start a review session for a deck.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "deck": { "name": "Deck", "description": "Deck name." }
      }
    },
    "create_deck": {
      "name": "Create deck",
      "description": "Create a new deck (use :: for nesting).",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "deck": { "name": "Deck", "description": "New deck name." }
      }
    },
    "add_tags": {
      "name": "Add tags",
      "description": "Add space-separated tags to notes.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "notes": { "name": "Note IDs", "description": "List of note IDs." },
        "tags": { "name": "Tags", "description": "Space-separated tags." }
      }
    },
    "remove_tags": {
      "name": "Remove tags",
      "description": "Remove space-separated tags from notes.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "notes": { "name": "Note IDs", "description": "List of note IDs." },
        "tags": { "name": "Tags", "description": "Space-separated tags." }
      }
    },
    "suspend": {
      "name": "Suspend cards",
      "description": "Suspend the given cards.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "cards": { "name": "Card IDs", "description": "List of card IDs." }
      }
    },
    "unsuspend": {
      "name": "Unsuspend cards",
      "description": "Unsuspend the given cards.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "cards": { "name": "Card IDs", "description": "List of card IDs." }
      }
    },
    "collection_stats_html": {
      "name": "Collection stats (HTML)",
      "description": "Return the HTML statistics report for the collection.",
      "fields": {
        "config_entry_id": { "name": "Anki instance", "description": "The Anki config entry to target." },
        "whole_collection": { "name": "Whole collection", "description": "Stats for the whole collection rather than the current deck." }
      }
    }
  }
}
```

- [ ] **Step 2: Create `translations/en.json` as a copy of `strings.json`**

```bash
cp custom_components/anki_connect/strings.json custom_components/anki_connect/translations/en.json
```

- [ ] **Step 3: Write `custom_components/anki_connect/translations/pt-BR.json`**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Conectar ao Anki",
        "description": "O Anki precisa estar aberto com o complemento AnkiConnect. Para acesso de outra máquina, defina ANKICONNECT_BIND_ADDRESS=0.0.0.0 na configuração do complemento.",
        "data": {
          "host": "Host",
          "port": "Porta",
          "name": "Nome",
          "api_key": "Chave de API (opcional)"
        }
      },
      "reconfigure": {
        "title": "Reconfigurar Anki",
        "description": "Atualize os dados de conexão desta instância do Anki.",
        "data": {
          "host": "Host",
          "port": "Porta",
          "name": "Nome",
          "api_key": "Chave de API (opcional)"
        }
      }
    },
    "error": {
      "cannot_connect": "Não foi possível acessar o AnkiConnect. Verifique host, porta, chave de API e se o Anki está aberto com o complemento ativado."
    },
    "abort": {
      "already_configured": "Esta instância do Anki já está configurada.",
      "reconfigure_successful": "Anki reconfigurado com sucesso."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Opções do Anki",
        "data": {
          "scan_interval": "Intervalo de atualização (segundos)"
        }
      }
    }
  },
  "entity": {
    "sensor": {
      "cards_reviewed_today": { "name": "Cartões revisados hoje" },
      "cards_due": { "name": "Cartões pendentes" },
      "new_cards": { "name": "Cartões novos" },
      "learning_cards": { "name": "Cartões em aprendizado" },
      "review_cards": { "name": "Cartões para revisão" },
      "total_cards": { "name": "Total de cartões" },
      "decks": { "name": "Baralhos" },
      "anki_connect_version": { "name": "Versão do AnkiConnect" },
      "profiles": { "name": "Perfis" },
      "tags": { "name": "Etiquetas" },
      "note_types": { "name": "Tipos de nota" },
      "media_directory": { "name": "Diretório de mídia" },
      "deck_cards_due": { "name": "Cartões pendentes" },
      "deck_new_cards": { "name": "Cartões novos" },
      "deck_learning_cards": { "name": "Cartões em aprendizado" },
      "deck_review_cards": { "name": "Cartões para revisão" },
      "deck_total_cards": { "name": "Total de cartões" }
    },
    "binary_sensor": {
      "review_session_active": { "name": "Sessão de revisão ativa" }
    },
    "button": {
      "sync": { "name": "Sincronizar" },
      "open_deck_browser": { "name": "Abrir lista de baralhos" },
      "show_question": { "name": "Mostrar pergunta" },
      "show_answer": { "name": "Mostrar resposta" },
      "start_card_timer": { "name": "Iniciar cronômetro do cartão" },
      "undo": { "name": "Desfazer" },
      "check_database": { "name": "Verificar banco de dados" },
      "reload_collection": { "name": "Recarregar coleção" },
      "clear_unused_tags": { "name": "Limpar etiquetas não usadas" },
      "remove_empty_notes": { "name": "Remover notas vazias" },
      "exit_anki": { "name": "Fechar o Anki" }
    }
  }
}
```

- [ ] **Step 4: Write the failing test `tests/test_diagnostics.py`**

```python
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
    assert diag["data"]["version"] == 6
    assert diag["data"]["deck_count"] == 1
    assert diag["data"]["cards_due"] == 3
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `uv run pytest tests/test_diagnostics.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.anki_connect.diagnostics'`

- [ ] **Step 6: Write `custom_components/anki_connect/diagnostics.py`**

```python
"""Diagnostics for the Anki integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY
from .coordinator import AnkiConnectConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AnkiConnectConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
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
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `uv run pytest tests/test_diagnostics.py -q`
Expected: PASS (1 passed)

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS (all tests)

- [ ] **Step 9: Commit**

```bash
git add custom_components/anki_connect/strings.json custom_components/anki_connect/translations custom_components/anki_connect/diagnostics.py tests/test_diagnostics.py
git commit -m "feat: add UI strings, en/pt-BR translations, and diagnostics"
```

---

## Task 11: Brand assets + README

**Files:**
- Create: `scripts/generate_brand.py`
- Create: `custom_components/anki_connect/brand/icon.svg`
- Create (generated): `custom_components/anki_connect/brand/{icon,icon@2x,logo,logo@2x,dark_icon,dark_icon@2x,dark_logo,dark_logo@2x}.png`
- Create: `README.md`

> The Anki brand mark is a blue four-pointed star. HA Brands no longer accepts PRs, so the assets ship inside the integration. This task recreates the Anki star as an SVG and rasterizes it to the PNG sizes HA expects (icon ≤256 square, logo, plus @2x and dark variants). The star is rendered on a transparent background so the same file works on light and dark themes.

- [ ] **Step 1: Write `custom_components/anki_connect/brand/icon.svg`**

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <path d="M128 8 L152 104 L248 128 L152 152 L128 248 L104 152 L8 128 L104 104 Z"
        fill="#0094D6"/>
</svg>
```

- [ ] **Step 2: Write `scripts/generate_brand.py`**

```python
"""Render the Anki brand mark SVG into the PNG sizes Home Assistant expects."""
from __future__ import annotations

from pathlib import Path

import cairosvg

BRAND_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "anki_connect" / "brand"
SVG = BRAND_DIR / "icon.svg"

# (filename, output pixel size). Logo and icon use the same square star mark.
TARGETS = {
    "icon.png": 256,
    "icon@2x.png": 512,
    "logo.png": 256,
    "logo@2x.png": 512,
    "dark_icon.png": 256,
    "dark_icon@2x.png": 512,
    "dark_logo.png": 256,
    "dark_logo@2x.png": 512,
}


def main() -> None:
    svg_bytes = SVG.read_bytes()
    for filename, size in TARGETS.items():
        cairosvg.svg2png(
            bytestring=svg_bytes,
            write_to=str(BRAND_DIR / filename),
            output_width=size,
            output_height=size,
        )
        print(f"wrote {filename} ({size}x{size})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Generate the PNGs**

```bash
cd /Users/hudsonbrendon/Github/ha-anki-connect
uv run python scripts/generate_brand.py
ls -1 custom_components/anki_connect/brand/
```

Expected: lists `icon.svg` plus the 8 generated PNGs.

- [ ] **Step 4: Write `README.md`** (English, logo at top — same layout as ha-retroarch)

````markdown
<p align="center">
  <img src="custom_components/anki_connect/brand/logo.png" alt="Anki" width="180">
</p>

<h1 align="center">Anki for Home Assistant</h1>

<p align="center">
  Monitor and control your <a href="https://apps.ankiweb.net/">Anki</a> collection from Home Assistant via the
  <a href="https://github.com/amikey/anki-connect">AnkiConnect</a> add-on.
</p>

<p align="center">
  <a href="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/validate.yaml"><img src="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/validate.yaml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/tests.yaml"><img src="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/tests.yaml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS"></a>
  <img src="https://img.shields.io/github/v/release/hudsonbrendon/ha-anki-connect" alt="Release">
</p>

## Features

- **Collection sensors** — cards reviewed today, cards due, new / learning / review / total cards, deck count.
- **Per-deck devices** — every deck becomes its own device with due / new / learning / review / total sensors, added automatically as decks appear.
- **Diagnostics** — AnkiConnect version, profiles, tags, note types, media directory.
- **Review session binary sensor** — on while a review is open in Anki.
- **Buttons** — sync, open deck browser, show question/answer, undo, check database, reload collection, clear unused tags, remove empty notes, exit Anki.
- **Services** — a generic `anki_connect.api` action that exposes *every* AnkiConnect command, plus typed helpers (`add_note`, `find_notes`, `notes_info`, `find_cards`, `gui_browse`, `gui_deck_overview`, `gui_deck_review`, `create_deck`, `add_tags`, `remove_tags`, `suspend`, `unsuspend`, `sync`, `collection_stats_html`).

## Requirements

1. **Anki** running on a machine reachable from Home Assistant.
2. The **[AnkiConnect](https://ankiweb.net/shared/info/2055492159)** add-on installed (code `2055492159`).
3. For access from another machine, allow LAN binding by setting an environment variable before launching Anki:

   ```bash
   export ANKICONNECT_BIND_ADDRESS=0.0.0.0
   ```

   Optionally set an `apiKey` in the AnkiConnect add-on config; enter the same key in the integration's setup dialog.

> Anki must be **open** for the integration to poll. While Anki is closed the entities show as unavailable.

## Installation

### HACS (recommended)

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Add `https://github.com/hudsonbrendon/ha-anki-connect` as category **Integration**.
3. Install **Anki**, then restart Home Assistant.

### Manual

Copy `custom_components/anki_connect` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

**Settings → Devices & Services → Add Integration → Anki.** Enter the host, port (default `8765`), a name, and an optional API key.

## Services

Call any AnkiConnect action directly:

```yaml
action: anki_connect.api
data:
  config_entry_id: <your entry id>
  action: getNumCardsReviewedByDay
response_variable: reviews
```

Add a note:

```yaml
action: anki_connect.add_note
data:
  config_entry_id: <your entry id>
  deck: "Spanish"
  model: "Basic"
  fields:
    Front: "hola"
    Back: "hello"
  tags: ["spanish"]
```

## Development

```bash
uv venv
uv pip install -r requirements_test.txt homeassistant
uv run pytest -q
```

## License

MIT
````

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_brand.py custom_components/anki_connect/brand README.md
git commit -m "feat: add Anki brand assets and README"
```

---

## Task 12: Finalize — validate, clean history, publish, release

**Files:** none (repo operations only)

- [ ] **Step 1: Run hassfest-equivalent local sanity checks + full suite with coverage**

```bash
cd /Users/hudsonbrendon/Github/ha-anki-connect
uv run python -c "import json; json.load(open('custom_components/anki_connect/manifest.json')); json.load(open('hacs.json')); json.load(open('custom_components/anki_connect/strings.json')); json.load(open('custom_components/anki_connect/translations/en.json')); json.load(open('custom_components/anki_connect/translations/pt-BR.json')); print('json ok')"
uv run pytest -q --cov=custom_components/anki_connect --cov-report=term-missing
```

Expected: `json ok` and all tests passing.

- [ ] **Step 2: Squash the per-task history into one clean commit**

Per the user's convention (clean history before first public push, no Claude co-author):

```bash
cd /Users/hudsonbrendon/Github/ha-anki-connect
git checkout --orphan release-main
git add -A
git commit -m "feat: Anki (AnkiConnect) Home Assistant integration

Collection and per-deck statistics sensors, review-session binary sensor,
sync/GUI/maintenance buttons, and the full AnkiConnect command surface as
services. HACS-installable with brand assets, en/pt-BR translations, and
auto-release CI."
git branch -D main
git branch -m main
```

Confirm a single commit authored solely by Hudson Brendon (no `Co-Authored-By`):

```bash
git log --format='%an <%ae>%n%b' -1
```

- [ ] **Step 3: Create the GitHub repo and push**

```bash
cd /Users/hudsonbrendon/Github/ha-anki-connect
gh repo create hudsonbrendon/ha-anki-connect --public --source=. --remote=origin --description "Home Assistant custom integration for Anki via the AnkiConnect add-on" --push
```

- [ ] **Step 4: Add HACS topics (so the repo validates / is discoverable)**

```bash
gh repo edit hudsonbrendon/ha-anki-connect --add-topic home-assistant --add-topic hacs --add-topic anki --add-topic ankiconnect --add-topic custom-component --add-topic integration
```

- [ ] **Step 5: Verify CI is green**

```bash
gh run list --repo hudsonbrendon/ha-anki-connect --limit 5
```

Expected: `Validate` and `Tests` workflows succeed on the pushed `main`.

- [ ] **Step 6: Confirm the auto-release fired**

The `release.yml` workflow runs on push to `main` touching `manifest.json` and creates tag `v0.1.0`:

```bash
gh release view v0.1.0 --repo hudsonbrendon/ha-anki-connect
```

If it did not trigger (first-push edge cases), create it manually once:

```bash
gh release create v0.1.0 --repo hudsonbrendon/ha-anki-connect --title v0.1.0 --generate-notes
```

Future releases happen automatically: bump `version` in `manifest.json`, commit, push to `main`.

- [ ] **Step 7: Smoke-test against the live add-on (optional, requires Anki running locally)**

In a real Home Assistant instance, add the integration pointing at `127.0.0.1:8765`, confirm the `sensor.anki_cards_reviewed_today` and per-deck sensors populate, press the `Sync` button, and call `anki_connect.api` with `action: version`.

---

## Self-Review

**1. Spec coverage**
- "custom component following the same pattern as the other repos" → Tasks 1–11 mirror `ha-retroarch` (coordinator, entity descriptions, config/options flow, services, brand/, en+pt-BR, hacs.json, CI). ✔
- "all types of information, commands, everything possible" → aggregate + per-deck + diagnostic sensors, review binary sensor, 11 buttons, generic `api` service exposing every action + 14 typed services. ✔
- "no Claude history in commits" → Task 12 squashes to one commit, log verified to have no `Co-Authored-By`; every commit message in the plan omits the trailer. ✔
- "logo / brand assets from official Anki logo, same standard, English README with image" → Task 11 generates the Anki star brand set and an English README with the logo at top. ✔
- "automatic distribution via releases in CI" → Task 1 `release.yml` (manifest-bump → `gh release --generate-notes`); verified in Task 12. ✔
- "English format, same as currently" → strings/README/code in English; pt-BR translation added like the other repos. ✔
- AnkiConnect specifics (binding, optional apiKey, Anki must run) documented in README + handled in config flow. ✔

**2. Placeholder scan** — every code step contains complete, runnable code; every test step contains real assertions; no "TODO"/"add error handling"/"similar to Task N". The one cross-task ordering caveat (`__init__.py` imports platforms/services created later) is called out explicitly in Task 4 with the resolution. ✔

**3. Type consistency** — `DOMAIN="anki_connect"`, `AnkiConnectClient.request(action, **params)`, `AnkiData`/`DeckStats` field names (`new`/`learn`/`review`/`total`, `.due`), coordinator `client`/`device_name`, `entry.runtime_data`, entity bases `AnkiEntity`/`AnkiDeckEntity`, translation keys (`deck_*` for per-deck sensors), and service names match across api/coordinator/entity/sensor/binary_sensor/button/services/diagnostics and their tests. The `getDeckStats` response is keyed by deck-id string with `deck_id/name/new_count/learn_count/review_count/total_in_deck` — consumed exactly that way in `coordinator._async_update_data`. ✔
