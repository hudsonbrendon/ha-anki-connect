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

    @property
    def available(self) -> bool:
        # Stay available (with last-known values) whenever we have ever had a
        # snapshot, even if Anki is currently closed and the data is offline.
        return self.coordinator.data is not None


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
        return (
            self.coordinator.data is not None
            and self._deck_name in self.coordinator.data.decks
        )
