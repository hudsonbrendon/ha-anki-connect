"""Fixtures for the Anki integration tests."""
import aiohttp
import aiohttp.connector
import homeassistant.helpers.aiohttp_client as _ha_aiohttp_client
import pytest

# pycares 5.x's c-ares event thread (``_run_safe_shutdown_loop``) is a lingering
# daemon thread that the HA test harness' ``verify_cleanup`` check rejects,
# failing every test that builds a client session. Swap the c-ares-backed
# AsyncResolver for the threaded resolver session-wide (at import, before any
# fixture builds a session), covering both the bare-session path
# (aiohttp.connector.DefaultResolver) and HA's explicit-connector path. Tests
# never resolve real hosts — aioclient_mock intercepts requests before DNS.
aiohttp.connector.DefaultResolver = aiohttp.resolver.ThreadedResolver
_ha_aiohttp_client.AsyncResolver = aiohttp.resolver.ThreadedResolver

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
