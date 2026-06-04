"""Smoke test that the package imports and core constants are wired."""
from custom_components.anki_connect.const import (
    ACTION_DECK_STATS,
    ACTION_REVIEW_ACTIVE,
    ACTION_REVIEWED_TODAY,
    API_VERSION,
    DEFAULT_PORT,
    DOMAIN,
)


def test_domain_and_defaults():
    assert DOMAIN == "anki_connect"
    assert DEFAULT_PORT == 8765
    assert API_VERSION == 6


def test_action_strings_match_ankiconnect_api():
    # These exact strings are the AnkiConnect v6 action names; a typo here
    # silently breaks polling, so guard the highest-risk ones.
    assert ACTION_DECK_STATS == "getDeckStats"
    assert ACTION_REVIEWED_TODAY == "getNumCardsReviewedToday"
    assert ACTION_REVIEW_ACTIVE == "guiReviewActive"
