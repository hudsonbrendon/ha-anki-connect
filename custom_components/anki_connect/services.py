"""Services for the Anki integration: a generic action call plus typed helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from .coordinator import AnkiDataUpdateCoordinator

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


def _get_coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> AnkiDataUpdateCoordinator:
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
