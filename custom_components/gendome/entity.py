"""Gendome 设备实体的公共实现。"""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GendomeDataUpdateCoordinator
from .models import GendomeDeviceState


class GendomeEntity(CoordinatorEntity[GendomeDataUpdateCoordinator]):
    """Gendome 云端实体基类。"""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GendomeDataUpdateCoordinator,
        device_id: str,
        entity_key: str,
        *,
        available_when_offline: bool = False,
    ) -> None:
        super().__init__(coordinator, context=device_id)
        self._device_id = device_id
        self._available_when_offline = available_when_offline
        device = self.device_state.device
        normalized_mac = "".join(char for char in device.mac.lower() if char.isalnum())
        self._attr_unique_id = f"{normalized_mac}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac)},
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            sw_version=device.software_version,
        )

    @property
    def device_state(self) -> GendomeDeviceState:
        """返回当前实体的内存设备状态。"""
        return self.coordinator.data.devices[self._device_id]

    @property
    def available(self) -> bool:
        """返回云端和设备是否可用。"""
        return bool(
            self.coordinator.last_update_success
            and (
                self._available_when_offline
                or self.device_state.device.online
            )
        )
