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
