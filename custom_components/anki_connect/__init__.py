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
