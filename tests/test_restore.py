"""Restore-on-restart: entities keep their last value across a HA restart.

``test_init.py::test_cold_start_with_anki_closed`` covers the case with no
prior data at all: collection sensors stay unavailable, which is correct —
there is nothing to restore. This file covers the harder case: Anki *was*
open in a previous run, HA restarts while Anki is closed, and the last
snapshot should come back from Home Assistant's restore-state storage
instead of showing unavailable again.
"""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, STATE_ON
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
    mock_restore_cache_with_extra_data,
)

from custom_components.anki_connect.api import AnkiConnectError
from custom_components.anki_connect.const import DEFAULT_PORT, DOMAIN


async def _setup_with_anki_closed(hass: HomeAssistant) -> MockConfigEntry:
    """Load the integration as if Anki were closed across the restart."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.anki_connect.coordinator."
        "AnkiDataUpdateCoordinator._async_update_data",
        side_effect=AnkiConnectError("Anki closed"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def test_collection_sensor_restores_last_value_after_restart(
    hass: HomeAssistant,
):
    """cards_due must show its pre-restart value, not go unavailable forever."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("sensor.anki_cards_due", "7"),
                {"native_value": 7, "native_unit_of_measurement": None},
            ),
        ),
    )

    await _setup_with_anki_closed(hass)

    state = hass.states.get("sensor.anki_cards_due")
    assert state is not None
    assert state.state == "7"


async def test_diagnostic_sensor_restores_last_value_after_restart(
    hass: HomeAssistant,
):
    """A diagnostic sensor (version) restores its already-typed last value."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("sensor.anki_ankiconnect_version", "6"),
                {"native_value": 6, "native_unit_of_measurement": None},
            ),
        ),
    )

    await _setup_with_anki_closed(hass)

    state = hass.states.get("sensor.anki_ankiconnect_version")
    assert state is not None
    assert state.state == "6"


async def test_review_active_binary_sensor_restores_after_restart(
    hass: HomeAssistant,
):
    """The review-active binary sensor restores its last on/off."""
    mock_restore_cache(
        hass, [State("binary_sensor.anki_review_session_active", STATE_ON)]
    )

    await _setup_with_anki_closed(hass)

    state = hass.states.get("binary_sensor.anki_review_session_active")
    assert state is not None
    assert state.state == "on"


async def test_connectivity_sensor_is_available_and_off_with_no_prior_data(
    hass: HomeAssistant,
):
    """Connectivity must report 'off', never 'unavailable', even cold."""
    await _setup_with_anki_closed(hass)

    state = hass.states.get("binary_sensor.anki_connected")
    assert state is not None
    assert state.state == "off"


async def test_connectivity_sensor_never_restores_a_stale_on(hass: HomeAssistant):
    """Connectivity is a live fact: a saved 'on' must never leak back in."""
    mock_restore_cache(hass, [State("binary_sensor.anki_connected", STATE_ON)])

    await _setup_with_anki_closed(hass)

    state = hass.states.get("binary_sensor.anki_connected")
    assert state is not None
    assert state.state == "off"
