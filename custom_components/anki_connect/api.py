"""Async HTTP client for the AnkiConnect add-on."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    ACTION_DECK_NAMES,
    ACTION_DECK_STATS,
    ACTION_MEDIA_DIR,
    ACTION_MODEL_NAMES,
    ACTION_PROFILES,
    ACTION_REVIEW_ACTIVE,
    ACTION_REVIEWED_BY_DAY,
    ACTION_REVIEWED_TODAY,
    ACTION_TAGS,
    ACTION_VERSION,
    API_VERSION,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class AnkiConnectError(Exception):
    """Raised when AnkiConnect returns an error or is unreachable."""


class AnkiConnectClient:
    """Talks to one AnkiConnect endpoint over HTTP."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession,
        *,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._url = f"http://{host}:{port}"
        self._session = session
        self._api_key = api_key
        self._timeout = timeout

    @property
    def url(self) -> str:
        """Return the configured endpoint URL."""
        return self._url

    async def request(self, action: str, **params: Any) -> Any:
        """POST one AnkiConnect action and return its ``result``."""
        _LOGGER.debug("AnkiConnect request '%s'", action)
        payload: dict[str, Any] = {"action": action, "version": API_VERSION}
        if params:
            payload["params"] = params
        if self._api_key:
            payload["key"] = self._api_key

        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.post(self._url, json=payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AnkiConnectError(
                f"AnkiConnect request '{action}' failed: {err}"
            ) from err

        if not isinstance(data, dict) or "error" not in data:
            raise AnkiConnectError(f"Unexpected AnkiConnect response: {data!r}")
        if data["error"] is not None:
            raise AnkiConnectError(str(data["error"]))
        return data.get("result")

    # --- Typed convenience wrappers used by the coordinator ---
    async def async_version(self) -> int | None:
        return await self.request(ACTION_VERSION)

    async def async_deck_names(self) -> list[str]:
        return await self.request(ACTION_DECK_NAMES) or []

    async def async_deck_stats(self, decks: list[str]) -> dict[str, dict]:
        return await self.request(ACTION_DECK_STATS, decks=decks) or {}

    async def async_num_reviewed_today(self) -> int:
        return await self.request(ACTION_REVIEWED_TODAY) or 0

    async def async_reviews_by_day(self) -> list[list]:
        return await self.request(ACTION_REVIEWED_BY_DAY) or []

    async def async_profiles(self) -> list[str]:
        return await self.request(ACTION_PROFILES) or []

    async def async_tags(self) -> list[str]:
        return await self.request(ACTION_TAGS) or []

    async def async_model_names(self) -> list[str]:
        return await self.request(ACTION_MODEL_NAMES) or []

    async def async_media_dir(self) -> str | None:
        # Returns None when Anki has no media folder configured (no fallback).
        return await self.request(ACTION_MEDIA_DIR)

    async def async_review_active(self) -> bool:
        return bool(await self.request(ACTION_REVIEW_ACTIVE))
