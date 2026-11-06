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

    remove_buttons = Mock()
    monkeypatch.setattr(
        "custom_components.gendome._async_remove_legacy_refresh_buttons",
        remove_buttons,
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
    remove_buttons.assert_called_once_with(hass, entry)
    assert "button" not in PLATFORMS
    assert entry.runtime_data.api is api_instance
    assert entry.runtime_data.coordinator is coordinator_instance


@pytest.mark.parametrize("legacy_count", [0, 1, 2])
def test_retired_refresh_buttons_removed_only_from_current_entry(
    monkeypatch, legacy_count
) -> None:
    """Remove old buttons safely, preserving other entities and user renames."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.gendome import _async_remove_legacy_refresh_buttons

    legacy = [
        SimpleNamespace(
            domain="button",
            platform="gendome",
            unique_id=f"mac{index}_refresh_state",
            entity_id=f"button.user_renamed_{index}",
        )
        for index in range(legacy_count)
    ]
    untouched = [
        SimpleNamespace(
            domain=domain, platform=platform, unique_id=unique_id,
            entity_id=entity_id,
        )
        for domain, platform, unique_id, entity_id in (
            ("switch", "gendome", "mac_ac_output", "switch.ac_output"),
            ("button", "gendome", "mac_identify", "button.identify"),
            ("button", "other", "mac_refresh_state", "button.other"),
        )
    ]
    entries = {item.entity_id: item for item in legacy + untouched}
    registry = SimpleNamespace(async_remove=Mock(side_effect=entries.pop))
    hass = object()
    entry = SimpleNamespace(entry_id="current-entry")
    monkeypatch.setattr(er, "async_get", Mock(return_value=registry))
    entries_for_entry = Mock(side_effect=lambda *_: list(entries.values()))
    monkeypatch.setattr(er, "async_entries_for_config_entry", entries_for_entry)

    _async_remove_legacy_refresh_buttons(hass, entry)
    _async_remove_legacy_refresh_buttons(hass, entry)

    entries_for_entry.assert_called_with(registry, "current-entry")
    assert registry.async_remove.call_count == legacy_count
    assert set(entries) == {item.entity_id for item in untouched}
