"""Gendome 诊断信息支持。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "refresh_token",
        "token",
        "email",
        "ip",
        "last_used_ip",
        "sn",
        "serial_number",
        "mac",
        "device_id",
        "deviceid",
        "user_id",
        "userid",
        "username",
    }
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """返回已脱敏的 Gendome 账号诊断信息。"""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    devices = []
    for state in coordinator.data.devices.values():
        devices.append(
            _redact(
                {
                    "device_id": state.device.device_id,
                    "mac": state.device.mac,
                    "name": state.device.name,
                    "model": state.device.model,
                    "online": state.device.online,
                    "wifi_version": state.device.wifi_version,
                    "mcu_version": state.device.mcu_version,
                    "states": dict(state.states),
                    "raw_properties": dict(state.raw_properties),
                    "update_time": state.update_time,
                }
            )
        )
    return {
        "config_entry": _redact(dict(entry.data)),
        "profile": _redact(
            {
                "user_id": coordinator.data.profile.user_id,
                "username": coordinator.data.profile.username,
                "email": coordinator.data.profile.email,
                "region": coordinator.data.profile.region,
                "scopes": coordinator.data.profile.scopes,
            }
        ),
        "last_update_success": coordinator.last_update_success,
        "last_error": _redact(runtime.api.last_error),
        "devices": devices,
    }


def _redact(value: Any, key: str | None = None) -> Any:
    """递归移除敏感信息并掩码处理稳定设备标识。"""
    normalized_key = (key or "").lower()
    if normalized_key in SENSITIVE_KEYS:
        if normalized_key in {
            "mac",
            "sn",
            "serial_number",
            "device_id",
            "deviceid",
            "user_id",
            "userid",
            "username",
        }:
            return _mask_identifier(value)
        return "**REDACTED**"
    if isinstance(value, Mapping):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_redact(item) for item in value]
    return value


def _mask_identifier(value: Any) -> str:
    text = str(value or "")
    return f"***{text[-4:]}" if text else "**REDACTED**"
