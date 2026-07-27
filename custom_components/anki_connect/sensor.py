"""Sensor platform for Anki: aggregate, diagnostic, and per-deck card counts."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    RestoreSensor,
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
        # MEASUREMENT, not TOTAL_INCREASING: this counter resets to 0 at
        # midnight, which TOTAL_INCREASING would misread as a meter rollover.
        state_class=SensorStateClass.MEASUREMENT,
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
        # Anki may be closed at startup, leaving no snapshot yet. Per-deck
        # sensors are then registered once the first successful poll arrives.
        if coordinator.data is None:
            return
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


class AnkiSensor(AnkiEntity, RestoreSensor):
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
        self._restored_value: StateType = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._restored_value = last_data.native_value

    @property
    def native_value(self) -> StateType:
        if self.coordinator.data is not None:
            return self.entity_description.value_fn(self.coordinator.data)
        return self._restored_value

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.attr_fn is None:
            return None
        if self.coordinator.data is None:
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
