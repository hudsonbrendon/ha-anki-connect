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
