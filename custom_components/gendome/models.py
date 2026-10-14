"""Gendome 云端 API 数据模型。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "on", "yes"}:
            return True
        if normalized in {"0", "false", "off", "no"}:
            return False
    return None


@dataclass(frozen=True, slots=True)
class GendomeProfile:
    """OAuth 账号资料。"""

    user_id: str
    username: str | None
    email: str | None
    region: str
    scopes: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GendomeProfile:
        """根据 OpenAPI 响应构建账号资料。"""
        user_id = value.get("userId")
        if user_id is None:
            raise ValueError("Profile response does not contain userId")
        return cls(
            user_id=str(user_id),
            username=_optional_string(value.get("username")),
            email=_optional_string(value.get("email")),
            region=str(value.get("region") or "GLOBAL").upper(),
            scopes=tuple(str(scope) for scope in value.get("scopes") or ()),
        )


@dataclass(frozen=True, slots=True)
class GendomeDevice:
    """Gendome 账号下已绑定的设备。"""

    device_id: str
    mac: str
    name: str
    manufacturer: str = "Gendome"
    model: str | None = None
    online: bool = False
    wifi_version: str | None = None
    mcu_version: str | None = None
    product_key: str | None = None
    zone_id: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> GendomeDevice:
        """根据 OpenAPI 响应构建设备对象。"""
        device_id = value.get("deviceId")
        mac = value.get("mac")
        if device_id is None or not mac:
            raise ValueError("Device response must contain deviceId and mac")
        online = _as_bool(value.get("online"))
        return cls(
            device_id=str(device_id),
            mac=str(mac),
            name=str(value.get("name") or value.get("model") or mac),
            manufacturer=str(value.get("manufacturer") or "Gendome"),
            model=_optional_string(value.get("model")),
            online=bool(online),
            wifi_version=_optional_string(value.get("wifiVersion")),
            mcu_version=_optional_string(value.get("mcuVersion")),
            product_key=_optional_string(value.get("productKey")),
            zone_id=_optional_string(value.get("zoneId")),
        )

    @property
    def software_version(self) -> str | None:
        """返回用于设备注册表的紧凑软件版本。"""
        versions = []
        if self.wifi_version:
            versions.append(f"Wi-Fi {self.wifi_version}")
        if self.mcu_version:
            versions.append(f"MCU {self.mcu_version}")
        return " / ".join(versions) or None


@dataclass(frozen=True, slots=True)
class GendomeDeviceState:
    """单个设备当前的语义化状态和原始状态。"""

    device: GendomeDevice
    states: Mapping[str, Any] = field(default_factory=dict)
    raw_properties: Mapping[str, Any] = field(default_factory=dict)
    update_time: str | None = None

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        device: GendomeDevice | None = None,
    ) -> GendomeDeviceState:
        """构建设备状态，并合并 /devices 返回的元数据。"""
        state_device = GendomeDevice.from_dict(value)
        if device is not None:
            online = _as_bool(value.get("online"))
            state_device = GendomeDevice(
                device_id=device.device_id,
                mac=device.mac,
                name=str(value.get("name") or device.name),
                manufacturer=str(value.get("manufacturer") or device.manufacturer),
                model=_optional_string(value.get("model")) or device.model,
                online=device.online if online is None else online,
                wifi_version=_optional_string(value.get("wifiVersion"))
                or device.wifi_version,
                mcu_version=_optional_string(value.get("mcuVersion"))
                or device.mcu_version,
                product_key=device.product_key,
                zone_id=device.zone_id,
            )
        states = dict(value.get("states") or {})
        states.setdefault("online", state_device.online)
        return cls(
            device=state_device,
            states=states,
            raw_properties=dict(value.get("rawProperties") or {}),
            update_time=_optional_string(value.get("updateTime")),
        )

    def value(self, key: str) -> Any:
        """返回语义化状态值。"""
        return self.states.get(key)

    def boolean(self, key: str) -> bool | None:
        """以布尔值形式返回语义化状态。"""
        return _as_bool(self.states.get(key))


@dataclass(frozen=True, slots=True)
class GendomeCoordinatorData:
    """Home Assistant 实体使用的全部缓存数据。"""

    profile: GendomeProfile
    devices: Mapping[str, GendomeDeviceState]
    schedules: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
