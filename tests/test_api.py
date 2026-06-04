"""Tests for the AnkiConnect HTTP client."""
from __future__ import annotations

import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.anki_connect.api import AnkiConnectClient, AnkiConnectError


def _client(hass, **kwargs) -> AnkiConnectClient:
    return AnkiConnectClient(
        "1.2.3.4", 8765, async_get_clientsession(hass), **kwargs
    )


async def test_request_returns_result(hass, aioclient_mock):
    aioclient_mock.post(
        "http://1.2.3.4:8765", json={"result": ["Default"], "error": None}
    )
    client = _client(hass)
    assert await client.async_deck_names() == ["Default"]


async def test_request_includes_action_version_and_params(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": {}, "error": None})
    client = _client(hass)
    await client.async_deck_stats(["Default"])
    sent = aioclient_mock.mock_calls[0][2]
    assert sent["action"] == "getDeckStats"
    assert sent["version"] == 6
    assert sent["params"] == {"decks": ["Default"]}
    assert "key" not in sent


async def test_request_omits_params_for_no_arg_action(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": 6, "error": None})
    client = _client(hass)
    await client.async_version()
    assert "params" not in aioclient_mock.mock_calls[0][2]


async def test_request_raises_on_malformed_response(hass, aioclient_mock):
    # Response missing the "error" key is not a valid AnkiConnect envelope.
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": "x"})
    client = _client(hass)
    with pytest.raises(AnkiConnectError):
        await client.async_version()


async def test_request_includes_api_key_when_configured(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", json={"result": 6, "error": None})
    client = _client(hass, api_key="s3cret")
    await client.async_version()
    assert aioclient_mock.mock_calls[0][2]["key"] == "s3cret"


async def test_request_raises_on_anki_error(hass, aioclient_mock):
    aioclient_mock.post(
        "http://1.2.3.4:8765", json={"result": None, "error": "collection is not open"}
    )
    client = _client(hass)
    with pytest.raises(AnkiConnectError, match="collection is not open"):
        await client.async_version()


async def test_request_raises_on_transport_error(hass, aioclient_mock):
    aioclient_mock.post("http://1.2.3.4:8765", status=500)
    client = _client(hass)
    with pytest.raises(AnkiConnectError):
        await client.async_version()


@pytest.mark.parametrize(
    ("result", "expected"), [(True, True), (False, False)]
)
async def test_review_active_coerces_bool(hass, aioclient_mock, result, expected):
    aioclient_mock.post(
        "http://1.2.3.4:8765", json={"result": result, "error": None}
    )
    client = _client(hass)
    assert await client.async_review_active() is expected


async def test_request_gives_up_after_repeated_disconnects(hass, aioclient_mock):
    # AnkiConnect closes keep-alive connections; persistent disconnects exhaust
    # the retries and surface as AnkiConnectError.
    aioclient_mock.post(
        "http://1.2.3.4:8765", exc=aiohttp.ServerDisconnectedError()
    )
    client = _client(hass)
    with pytest.raises(AnkiConnectError):
        await client.async_version()
    assert aioclient_mock.call_count == 3


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    def raise_for_status(self) -> None:
        pass

    async def json(self, content_type=None) -> dict:
        return self._payload


class _FlakySession:
    """Fails with ServerDisconnectedError for the first N posts, then succeeds."""

    def __init__(self, fail_times: int, payload: dict) -> None:
        self.calls = 0
        self._fail = fail_times
        self._payload = payload

    def post(self, url, json=None):
        self.calls += 1
        if self.calls <= self._fail:
            raise aiohttp.ServerDisconnectedError()
        return _FakeResponse(self._payload)


async def test_request_retries_on_disconnect_then_succeeds():
    session = _FlakySession(1, {"result": ["Default"], "error": None})
    client = AnkiConnectClient("1.2.3.4", 8765, session)
    assert await client.async_deck_names() == ["Default"]
    assert session.calls == 2  # failed once, then a fresh connection worked
