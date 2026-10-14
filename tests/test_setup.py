"""Tests for config-entry setup after the browser OAuth callback."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.gendome import async_setup_entry
from custom_components.gendome.const import (
    DEFAULT_API_BASE_URL,
    PLATFORMS,
    PUBLIC_OAUTH_IMPLEMENTATION,
)


@pytest.mark.asyncio
async def test_public_oauth_entry_loads_devices_and_platforms(monkeypatch) -> None:
    """A public OAuth entry performs its first refresh before loading entities."""
    coordinator_instance = SimpleNamespace(
        async_config_entry_first_refresh=AsyncMock()
    )
    coordinator_factory = Mock(return_value=coordinator_instance)
    api_instance = object()
    api_factory = Mock(return_value=api_instance)

    import custom_components.gendome.api as api_module
    import custom_components.gendome.coordinator as coordinator_module

    monkeypatch.setattr(api_module, "GendomeApiClient", api_factory)
    monkeypatch.setattr(
        coordinator_module, "GendomeDataUpdateCoordinator", coordinator_factory
    )

    config_entries = SimpleNamespace(async_forward_entry_setups=AsyncMock())
    hass = SimpleNamespace(
        data={},
        config=SimpleNamespace(components={"my"}),
        config_entries=config_entries,
    )
    entry = SimpleNamespace(
        data={
            "auth_implementation": PUBLIC_OAUTH_IMPLEMENTATION,
            "token": {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "expires_at": 4_102_444_800,
            },
            "api_base_url": DEFAULT_API_BASE_URL,
        },
        runtime_data=None,
    )

    assert await async_setup_entry(hass, entry) is True

    coordinator_instance.async_config_entry_first_refresh.assert_awaited_once_with()
    config_entries.async_forward_entry_setups.assert_awaited_once_with(
        entry, PLATFORMS
    )
    assert entry.runtime_data.api is api_instance
    assert entry.runtime_data.coordinator is coordinator_instance
