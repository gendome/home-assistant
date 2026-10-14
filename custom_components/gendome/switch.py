"""Gendome 设备控制项的开关实体。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import GendomeApiError
from .const import (
    COMMAND_SET_AC_INPUT,
    COMMAND_SET_AC_OUTPUT,
    COMMAND_SET_BUZZER,
    COMMAND_SET_DC_OUTPUT,
    DOMAIN,
)
from .entity import GendomeEntity


@dataclass(frozen=True, kw_only=True)
class GendomeSwitchDescription(SwitchEntityDescription):
    """描述一个 Gendome 开关。"""

    state_key: str
    command: str
    optional: bool = False


SWITCHES: tuple[GendomeSwitchDescription, ...] = (
    GendomeSwitchDescription(
        key="ac_input",
        translation_key="ac_input",
        state_key="acInputEnabled",
        command=COMMAND_SET_AC_INPUT,
        icon="mdi:transmission-tower-import",
        optional=True,
    ),
    GendomeSwitchDescription(
        key="ac_output",
        translation_key="ac_output",
        state_key="acOutputEnabled",
        command=COMMAND_SET_AC_OUTPUT,
        icon="mdi:power-plug-output",
    ),
    GendomeSwitchDescription(
        key="dc_output",
        translation_key="dc_output",
        state_key="dcOutputEnabled",
        command=COMMAND_SET_DC_OUTPUT,
        icon="mdi:current-dc",
    ),
    GendomeSwitchDescription(
        key="buzzer",
        translation_key="buzzer",
        state_key="buzzerEnabled",
        command=COMMAND_SET_BUZZER,
        icon="mdi:volume-high",
        optional=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """初始化 Gendome 开关实体。"""
    coordinator = entry.runtime_data.coordinator
    entities: list[SwitchEntity] = []
    for device_id, state in coordinator.data.devices.items():
        for description in SWITCHES:
            if not description.optional or description.state_key in state.states:
                entities.append(GendomeSwitch(coordinator, device_id, description))
        entities.append(GendomeScheduledChargingSwitch(coordinator, device_id))
    async_add_entities(entities)


class GendomeSwitch(GendomeEntity, SwitchEntity):
    """由命令驱动的 Gendome 开关。"""

    entity_description: GendomeSwitchDescription

    def __init__(self, coordinator, device_id: str, description) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.device_state.boolean(self.entity_description.state_key)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        try:
            await self.coordinator.api.async_send_and_wait(
                self._device_id,
                self.entity_description.command,
                {"enabled": enabled},
            )
        except GendomeApiError as err:
            raise _control_error(err) from err
        await self.coordinator.async_request_refresh()


class GendomeScheduledChargingSwitch(GendomeEntity, SwitchEntity):
    """启用或停用已有的定时充电计划。"""

    _attr_translation_key = "scheduled_charging"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id, "scheduled_charging")

    @property
    def is_on(self) -> bool | None:
        schedule = self.coordinator.data.schedules.get(self._device_id)
        if not schedule:
            return None
        value = schedule.get("status", schedule.get("open"))
        if isinstance(value, bool):
            return value
        if value is None:
            return None
        return str(value).strip().lower() in {"1", "true", "on"}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        try:
            schedule = await self.coordinator.api.async_set_charging_schedule_enabled(
                self._device_id, enabled
            )
        except GendomeApiError as err:
            raise _control_error(err) from err
        self.coordinator.async_set_schedule(self._device_id, dict(schedule))


def _control_error(err: GendomeApiError) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="command_failed",
        translation_placeholders={"message": str(err)},
    )
