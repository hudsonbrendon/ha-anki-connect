"""Tests for the Anki review-active binary sensor."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN
from custom_components.anki_connect.coordinator import AnkiData


async def _setup(hass, snapshot: AnkiData) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.anki_connect.coordinator.AnkiDataUpdateCoordinator._async_update_data",
        return_value=snapshot,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_review_active_on(hass):
    await _setup(hass, AnkiData(available=True, version=6, review_active=True))
    assert hass.states.get("binary_sensor.anki_review_session_active").state == "on"


async def test_review_active_off(hass):
    await _setup(hass, AnkiData(available=True, version=6, review_active=False))
    assert hass.states.get("binary_sensor.anki_review_session_active").state == "off"


async def test_connectivity_on(hass):
    await _setup(hass, AnkiData(available=True, version=6))
    assert hass.states.get("binary_sensor.anki_connected").state == "on"


async def test_connectivity_off(hass):
    await _setup(hass, AnkiData(available=False, version=6))
    assert hass.states.get("binary_sensor.anki_connected").state == "off"
