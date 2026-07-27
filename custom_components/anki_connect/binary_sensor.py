"""Binary sensor platform for Anki."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
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
        self._restored_is_on: bool | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in (STATE_ON, STATE_OFF):
            self._restored_is_on = last_state.state == STATE_ON

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is not None:
            return self.coordinator.data.review_active
        return self._restored_is_on


class AnkiConnectivityBinarySensor(AnkiEntity, BinarySensorEntity):
    """Reports whether Anki desktop is currently reachable.

    Unlike the other entities, this one always stays available (even with
    no snapshot at all, e.g. right after a cold HA restart with Anki
    closed) so it can honestly report "off" instead of going unavailable.
    It never restores a saved "on": connectivity is a live fact, not a
    value worth remembering — a stale "on" must never leak back in.
    """

    _attr_translation_key = "connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: AnkiDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_connected"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.available
