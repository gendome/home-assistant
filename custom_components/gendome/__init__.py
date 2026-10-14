"""Gendome Home Assistant 集成。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .const import (
    CONF_API_BASE_URL,
    CONF_ENVIRONMENT,
    DEFAULT_API_BASE_URL,
    ENVIRONMENT,
    PLATFORMS,
    REVOKE_URL,
)

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .api import GendomeApiClient
    from .coordinator import GendomeDataUpdateCoordinator


@dataclass(slots=True)
class GendomeRuntimeData:
    """单个配置项持有的运行时对象。"""

    api: GendomeApiClient
    coordinator: GendomeDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """根据 OAuth2 配置项初始化 Gendome 集成。"""
    from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
    from homeassistant.helpers import config_entry_oauth2_flow

    from .api import GendomeApiClient
    from .coordinator import GendomeDataUpdateCoordinator
    from .oauth import async_get_entry_oauth2_implementation

    stored_environment = entry.data.get(CONF_ENVIRONMENT)
    if stored_environment and stored_environment != ENVIRONMENT:
        raise ConfigEntryError(
            "This Gendome entry is not a production entry. Remove it and add "
            "Gendome again to connect to the production service."
        )

    try:
        implementation = await async_get_entry_oauth2_implementation(hass, entry)
    except config_entry_oauth2_flow.ImplementationUnavailableError as err:
        raise ConfigEntryNotReady(
            "The Gendome OAuth implementation is temporarily unavailable"
        ) from err
    oauth_session = config_entry_oauth2_flow.OAuth2Session(
        hass, entry, implementation
    )
    api = GendomeApiClient(
        oauth_session,
        str(entry.data.get(CONF_API_BASE_URL, DEFAULT_API_BASE_URL)),
    )
    coordinator = GendomeDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = GendomeRuntimeData(api=api, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载 Gendome 配置项。"""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """删除集成配置项时，撤销对应的 Gendome Token。"""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    token = entry.data.get("token") or {}
    access_token = token.get("access_token")
    if not access_token:
        return

    try:
        response = await async_get_clientsession(hass).post(
            REVOKE_URL,
            data={"token": access_token},
        )
        if response.status >= 400:
            _LOGGER.warning(
                "Unable to revoke Gendome authorization while removing entry: %s",
                response.status,
            )
    except Exception:
        _LOGGER.warning(
            "Unable to contact Gendome while revoking the removed entry",
            exc_info=True,
        )
