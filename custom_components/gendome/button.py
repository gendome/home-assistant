"""Gendome 设备的按钮实体。"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import GendomeApiError
from .const import COMMAND_REFRESH_STATE, DOMAIN
from .entity import GendomeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """初始化 Gendome 刷新按钮。"""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GendomeRefreshButton(coordinator, device_id)
        for device_id in coordinator.data.devices
    )


class GendomeRefreshButton(GendomeEntity, ButtonEntity):
    """立即请求并获取设备最新状态。"""

    _attr_translation_key = "refresh_state"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "refresh_state")

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.async_send_and_wait(
                self._device_id, COMMAND_REFRESH_STATE
            )
        except GendomeApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"message": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()
