"""Gendome 能源设备的传感器实体。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .duration import duration_minutes, format_duration_minutes
from .entity import GendomeEntity


@dataclass(frozen=True, kw_only=True)
class GendomeSensorEntityDescription(SensorEntityDescription):
    """描述一个 Gendome 传感器。"""

    state_key: str
    required: bool = True
    format_duration: bool = False


SENSORS: tuple[GendomeSensorEntityDescription, ...] = (
    GendomeSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        state_key="batterySoc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="remaining_time",
        translation_key="remaining_time",
        state_key="remainingTime",
        format_duration=True,
    ),
    GendomeSensorEntityDescription(
        key="charge_remaining_time",
        translation_key="charge_remaining_time",
        state_key="chargeRemainingTime",
        required=False,
        format_duration=True,
    ),
    GendomeSensorEntityDescription(
        key="discharge_remaining_time",
        translation_key="discharge_remaining_time",
        state_key="dischargeRemainingTime",
        required=False,
        format_duration=True,
    ),
    GendomeSensorEntityDescription(
        key="input_total_power",
        translation_key="input_total_power",
        state_key="inputTotalPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="ac_input_power",
        translation_key="ac_input_power",
        state_key="acInputPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="solar_input_power",
        translation_key="solar_input_power",
        state_key="solarInputPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="wind_input_power",
        translation_key="wind_input_power",
        state_key="windInputPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        required=False,
    ),
    GendomeSensorEntityDescription(
        key="output_total_power",
        translation_key="output_total_power",
        state_key="outputTotalPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="ac_output_power",
        translation_key="ac_output_power",
        state_key="acOutputPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="dc_output_power",
        translation_key="dc_output_power",
        state_key="dcOutputPower",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GendomeSensorEntityDescription(
        key="ac_charge_power_setting",
        translation_key="ac_charge_power_setting",
        state_key="acChargePowerSetting",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    GendomeSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        state_key="firmwareVersion",
        required=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """初始化 Gendome 传感器。"""
    coordinator = entry.runtime_data.coordinator
    entities = []
    for device_id, state in coordinator.data.devices.items():
        for description in SENSORS:
            if description.required or description.state_key in state.states:
                entities.append(GendomeSensor(coordinator, device_id, description))
    async_add_entities(entities)


class GendomeSensor(GendomeEntity, SensorEntity):
    """只读的 Gendome 状态值。"""

    entity_description: GendomeSensorEntityDescription

    def __init__(self, coordinator, device_id: str, description) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """返回协调器中最新的状态值。"""
        value = self.device_state.value(self.entity_description.state_key)
        if self.entity_description.format_duration:
            return format_duration_minutes(
                value,
                self.coordinator.hass.config.language,
            )
        return value

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """为时长自动化和诊断信息提供原始分钟数。"""
        if not self.entity_description.format_duration:
            return None
        minutes = duration_minutes(
            self.device_state.value(self.entity_description.state_key)
        )
        return {"minutes": minutes} if minutes is not None else None
