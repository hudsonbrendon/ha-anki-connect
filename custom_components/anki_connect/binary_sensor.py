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
    """Set up the Anki binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            AnkiReviewActiveBinarySensor(coordinator),
            AnkiConnectivityBinarySensor(coordinator),
        ]
    )


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


class AnkiConnectivityBinarySensor(AnkiEntity, BinarySensorEntity):
    """Reports whether Anki desktop is currently reachable.

    Unlike the other entities, this one stays available even when Anki is
    closed so it can report "off" and surface the offline state to the user.
    """

    _attr_translation_key = "connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: AnkiDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_connected"

    @property
    def available(self) -> bool:
        # Stay available so it can report "off" while Anki is closed.
        return self.coordinator.data is not None

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.available
