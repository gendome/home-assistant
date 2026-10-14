"""Gendome 设备统一数据协调器。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    GendomeApiClient,
    GendomeApiError,
    GendomeAuthError,
    GendomePermissionError,
    GendomeRateLimitError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import GendomeCoordinatorData, GendomeDevice, GendomeDeviceState

_LOGGER = logging.getLogger(__name__)


class GendomeDataUpdateCoordinator(DataUpdateCoordinator[GendomeCoordinatorData]):
    """通过一次统一轮询获取账号下全部设备状态。"""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: GendomeApiClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )
        self.api = api
        self._profile = None
        self._schedules: dict[str, dict[str, Any]] = {}

    async def _async_setup(self) -> None:
        """一次性加载账号元数据和初始定时充电计划。"""
        try:
            self._profile = await self.api.async_get_profile()
            devices = await self.api.async_get_devices()
        except GendomeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GendomeApiError as err:
            raise UpdateFailed(str(err)) from err

        schedule_results = await asyncio.gather(
            *(self._async_get_schedule(device) for device in devices)
        )
        self._schedules = {
            device_id: schedule
            for device_id, schedule in schedule_results
            if schedule is not None
        }

    async def _async_get_schedule(
        self, device: GendomeDevice
    ) -> tuple[str, dict[str, Any] | None]:
        try:
            schedule = await self.api.async_get_charging_schedule(device.device_id)
            return device.device_id, dict(schedule)
        except (GendomePermissionError, GendomeApiError):
            _LOGGER.debug(
                "Charging schedule is unavailable for device %s", device.device_id
            )
            return device.device_id, None

    async def _async_update_data(self) -> GendomeCoordinatorData:
        """获取设备发现元数据和全部语义化状态。"""
        try:
            devices = await self.api.async_get_devices()
            device_map = {device.device_id: device for device in devices}
            states = await self.api.async_get_states(device_map)
        except GendomeAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except GendomeRateLimitError as err:
            raise UpdateFailed(str(err)) from err
        except GendomeApiError as err:
            raise UpdateFailed(str(err)) from err

        for device in devices:
            if device.device_id not in states:
                offline_device = replace(device, online=False)
                states[device.device_id] = GendomeDeviceState(
                    device=offline_device,
                    states={"online": False},
                )

        if self._profile is None:
            raise UpdateFailed("Gendome profile was not initialized")
        return GendomeCoordinatorData(
            profile=self._profile,
            devices=states,
            schedules=self._schedules,
        )

    def async_set_schedule(self, device_id: str, schedule: dict[str, Any]) -> None:
        """控制请求成功后，更新单个设备的缓存定时计划。"""
        self._schedules = {**self._schedules, device_id: dict(schedule)}
        if self.data is not None:
            self.async_set_updated_data(
                replace(self.data, schedules=dict(self._schedules))
            )
