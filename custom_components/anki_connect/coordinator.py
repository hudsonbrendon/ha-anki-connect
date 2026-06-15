"""DataUpdateCoordinator and snapshot models for the Anki integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AnkiConnectClient, AnkiConnectError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

type AnkiConnectConfigEntry = ConfigEntry["AnkiDataUpdateCoordinator"]


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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
        """Number of decks in the collection."""
        return len(self.decks)

    @property
    def new_cards(self) -> int:
        """New cards waiting across all decks."""
        return sum(deck.new for deck in self.decks.values())

    @property
    def learning_cards(self) -> int:
        """Cards in the learning step across all decks."""
        return sum(deck.learn for deck in self.decks.values())

    @property
    def review_cards(self) -> int:
        """Cards due for review across all decks."""
        return sum(deck.review for deck in self.decks.values())

    @property
    def cards_due(self) -> int:
        """Total cards waiting to be studied across all decks."""
        return sum(deck.due for deck in self.decks.values())

    @property
    def total_cards(self) -> int:
        """Total cards in all decks."""
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
        # Rarely-changing fields fetched once and cached. A dedicated flag
        # (rather than a None sentinel) so a legitimately falsy/None value
        # from AnkiConnect is still cached instead of refetched every cycle.
        self._static_fetched = False
        self._version: int | None = None
        self._profiles: list[str] | None = None
        self._media_dir: str | None = None

    async def _async_update_data(self) -> AnkiData:
        try:
            if not self._static_fetched:
                self._version = await self.client.async_version()
                self._profiles = await self.client.async_profiles()
                self._media_dir = await self.client.async_media_dir()
                self._static_fetched = True

            deck_names = await self.client.async_deck_names()
            raw = await self.client.async_deck_stats(deck_names) if deck_names else {}
            reviewed = await self.client.async_num_reviewed_today()
            review_active = await self.client.async_review_active()
            tags = await self.client.async_tags()
            models = await self.client.async_model_names()
        except AnkiConnectError as err:
            # Anki may be closed: keep the last-known snapshot (marked offline)
            # so entities retain their values instead of going unavailable.
            if self.data is not None:
                return replace(self.data, available=False)
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
