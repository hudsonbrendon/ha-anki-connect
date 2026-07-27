"""Base entities for the Anki integration."""
from __future__ import annotations

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AnkiDataUpdateCoordinator


class AnkiEntity(RestoreEntity, CoordinatorEntity[AnkiDataUpdateCoordinator]):
    """Common device info for collection-wide Anki entities.

    ``coordinator.data`` already keeps its last value while Anki is merely
    closed within one running process (see coordinator.py) — but that cache
    lives in process memory, so a Home Assistant *restart* still reborns it
    as ``None``. This base class closes that gap: it remembers, via
    ``RestoreEntity``, whether this entity had a real (non-unavailable,
    non-unknown) state before the restart, and factors that into
    ``available``.

    ``AnkiConnectivityBinarySensor`` overrides ``available`` itself (always
    ``True``) and never restores its own ``is_on``, matching the same
    connectivity-sensor exception used across the other integrations.
    """

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
        self._restored_available = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        self._restored_available = (
            last_state is not None
            and last_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
        )

    @property
    def available(self) -> bool:
        # Stay available (with last-known values) whenever we have ever had a
        # snapshot, even if Anki is currently closed and the data is offline,
        # or a previous run left a valid state to restore.
        return self.coordinator.data is not None or self._restored_available


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
