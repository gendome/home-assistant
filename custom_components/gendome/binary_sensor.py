"""Gendome 设备的二进制传感器实体。"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import GendomeEntity


@dataclass(frozen=True, kw_only=True)
class GendomeBinarySensorDescription(BinarySensorEntityDescription):
    """描述一个 Gendome 二进制传感器。"""

    state_key: str


BINARY_SENSORS: tuple[GendomeBinarySensorDescription, ...] = (
    GendomeBinarySensorDescription(
        key="online",
        translation_key="online",
        state_key="online",
        icon="mdi:cloud-check",
    ),
    GendomeBinarySensorDescription(
        key="charging",
        translation_key="charging",
        state_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    GendomeBinarySensorDescription(
        key="discharging",
        translation_key="discharging",
        state_key="discharging",
        icon="mdi:battery-arrow-down",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """初始化 Gendome 二进制传感器。"""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        GendomeBinarySensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in BINARY_SENSORS
    )


class GendomeBinarySensor(GendomeEntity, BinarySensorEntity):
    """Gendome 布尔状态值实体。"""

    entity_description: GendomeBinarySensorDescription

    def __init__(self, coordinator, device_id: str, description) -> None:
        super().__init__(
            coordinator,
            device_id,
            description.key,
            available_when_offline=description.state_key == "online",
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """返回最新的布尔状态值。"""
        return self.device_state.boolean(self.entity_description.state_key)
