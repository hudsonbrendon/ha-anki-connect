"""Tests for the Anki config and options flow."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.anki_connect.api import AnkiConnectError
from custom_components.anki_connect.const import CONF_API_KEY, DEFAULT_PORT, DOMAIN


async def test_user_flow_success(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        return_value=6,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.2.3.4",
                CONF_PORT: DEFAULT_PORT,
                CONF_NAME: "Anki",
                CONF_API_KEY: "",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Anki"
    assert result["data"][CONF_HOST] == "1.2.3.4"


async def test_user_flow_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        side_effect=AnkiConnectError("unreachable"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_aborts(hass):
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.2.3.4:8765",
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        return_value=6,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_updates_host_and_unique_id(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.2.3.4:8765",
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        return_value=6,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "5.6.7.8", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "5.6.7.8"
    assert entry.unique_id == "5.6.7.8:8765"


async def test_reconfigure_cannot_connect(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1.2.3.4:8765",
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    with patch(
        "custom_components.anki_connect.config_flow.AnkiConnectClient.async_version",
        side_effect=AnkiConnectError("unreachable"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "5.6.7.8", CONF_PORT: DEFAULT_PORT, CONF_NAME: "Anki"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_sets_scan_interval(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 30}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 30


async def test_options_flow_rejects_below_minimum(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    # Below the vol.Range(min=5) bound, so schema validation rejects it.
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 4}
        )
