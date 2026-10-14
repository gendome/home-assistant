"""Gendome 设备设置项的数值实体。"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import GendomeApiError
from .const import (
    BEIYITONG_PRODUCT_KEYS,
    COMMAND_SET_AC_CHARGE_POWER,
    COMMAND_SET_BATTERY_RANGE,
    DOMAIN,
    PRODUCT_KEY_GO_1000,
)
from .entity import GendomeEntity


@dataclass(frozen=True, kw_only=True)
class GendomeNumberDescription(NumberEntityDescription):
    """描述一个 Gendome 数值设置项。"""

    state_key: str
    command: str


NUMBERS: tuple[GendomeNumberDescription, ...] = (
    GendomeNumberDescription(
        key="ac_charge_power_limit",
        translation_key="ac_charge_power_limit",
        state_key="acChargePowerSetting",
        command=COMMAND_SET_AC_CHARGE_POWER,
        native_min_value=0,
        native_max_value=3000,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
        icon="mdi:battery-charging-high",
    ),
    GendomeNumberDescription(
        key="battery_protection_lower_soc",
        translation_key="battery_protection_lower_soc",
        state_key="batteryProtectionLowerSoc",
        command=COMMAND_SET_BATTERY_RANGE,
        native_min_value=0,
        native_max_value=99,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
    GendomeNumberDescription(
        key="battery_protection_upper_soc",
        translation_key="battery_protection_upper_soc",
        state_key="batteryProtectionUpperSoc",
        command=COMMAND_SET_BATTERY_RANGE,
        native_min_value=1,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """初始化 Gendome 数值实体。"""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GendomeNumber(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in NUMBERS
    )


class GendomeNumber(GendomeEntity, NumberEntity):
    """经过校验的 Gendome 数值设置项。"""

    entity_description: GendomeNumberDescription

    def __init__(self, coordinator, device_id: str, description) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._apply_device_limits()

    def _apply_device_limits(self) -> None:
        product_key = self.device_state.device.product_key
        if product_key in BEIYITONG_PRODUCT_KEYS:
            if self.entity_description.key == "ac_charge_power_limit":
                self._attr_native_min_value = 60
                self._attr_native_max_value = (
                    1000 if product_key == PRODUCT_KEY_GO_1000 else 1500
                )
                self._attr_native_step = 10
            elif self.entity_description.key == "battery_protection_lower_soc":
                self._attr_native_min_value = 0
                self._attr_native_max_value = 30
                self._attr_native_step = 10
            elif self.entity_description.key == "battery_protection_upper_soc":
                self._attr_native_min_value = 50
                self._attr_native_max_value = 100
                self._attr_native_step = 10
            return

        if self.entity_description.key != "ac_charge_power_limit":
            return
        model = (self.device_state.device.model or "").lower()
        model_limits = {"go 300": 300, "go 800": 800, "home 3000": 3000}
        for name, limit in model_limits.items():
            if name in model:
                self._attr_native_max_value = limit
                break

    @property
    def native_value(self) -> float | None:
        value = self.device_state.value(self.entity_description.state_key)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        integer_value = int(value)
        if self.entity_description.command == COMMAND_SET_AC_CHARGE_POWER:
            payload = {"power": integer_value}
        else:
            payload = self._battery_range_payload(integer_value)
        try:
            await self.coordinator.api.async_send_and_wait(
                self._device_id, self.entity_description.command, payload
            )
        except GendomeApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"message": str(err)},
            ) from err
        await self.coordinator.async_request_refresh()

    def _battery_range_payload(self, value: int) -> dict[str, int]:
        states = self.device_state.states
        lower = _int_or_none(states.get("batteryProtectionLowerSoc"))
        upper = _int_or_none(states.get("batteryProtectionUpperSoc"))
        if self.entity_description.key == "battery_protection_lower_soc":
            lower = value
        else:
            upper = value
        if lower is None or upper is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="battery_range_unavailable",
            )
        if not 0 <= lower < upper <= 100:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="invalid_battery_range",
            )
        return {"lowerSoc": lower, "upperSoc": upper}


def _int_or_none(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
