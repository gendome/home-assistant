"""Gendome Home Assistant OpenAPI 异步客户端。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.parse import quote
from uuid import uuid4

from aiohttp import ClientError, ClientResponse, ClientResponseError

from .const import (
    COMMAND_POLL_INTERVAL_SECONDS,
    COMMAND_TIMEOUT_SECONDS,
    DEFAULT_API_BASE_URL,
    FAILED_COMMAND_STATUSES,
    OPENAPI_PREFIX,
    REQUEST_TIMEOUT_SECONDS,
    TERMINAL_COMMAND_STATUSES,
)
from .models import GendomeDevice, GendomeDeviceState, GendomeProfile


class AsyncRequester(Protocol):
    """由 OAuth2Session 或测试适配器提供的请求接口。"""

    async def async_request(
        self, method: str, url: str, **kwargs: Any
    ) -> ClientResponse:
        """发起携带认证信息的请求。"""


class GendomeApiError(Exception):
    """Gendome API 基础异常。"""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class GendomeAuthError(GendomeApiError):
    """OAuth 凭据无效或已撤销。"""


class GendomePermissionError(GendomeApiError):
    """OAuth 授权不包含所需的权限范围。"""


class GendomeRateLimitError(GendomeApiError):
    """已达到云端 API 的频率限制。"""

    def __init__(self, message: str, *, retry_after: int = 60) -> None:
        super().__init__(message, code="RATE_LIMITED")
        self.retry_after = retry_after


class GendomeConnectionError(GendomeApiError):
    """无法连接云端 API。"""


class GendomeCommandError(GendomeApiError):
    """设备命令执行失败或超时。"""


class GendomeApiClient:
    """对接 Java HomeAssistantController 接口协议的客户端。"""

    def __init__(
        self,
        requester: AsyncRequester,
        api_base_url: str = DEFAULT_API_BASE_URL,
    ) -> None:
        self._requester = requester
        self._base_url = api_base_url.rstrip("/")
        self.last_error: dict[str, Any] | None = None

    async def async_get_profile(self) -> GendomeProfile:
        data = await self._request("GET", "/profile")
        return GendomeProfile.from_dict(_require_mapping(data, "profile"))

    async def async_get_devices(self) -> list[GendomeDevice]:
        data = await self._request("GET", "/devices")
        if not isinstance(data, list):
            raise GendomeApiError("Devices response is not a list")
        return [
            GendomeDevice.from_dict(_require_mapping(item, "device"))
            for item in data
        ]

    async def async_get_states(
        self, devices: Mapping[str, GendomeDevice]
    ) -> dict[str, GendomeDeviceState]:
        data = await self._request("GET", "/devices/states")
        if not isinstance(data, list):
            raise GendomeApiError("Device states response is not a list")
        result: dict[str, GendomeDeviceState] = {}
        for item in data:
            item_mapping = _require_mapping(item, "device state")
            device_id = str(item_mapping.get("deviceId") or "")
            state = GendomeDeviceState.from_dict(item_mapping, devices.get(device_id))
            result[state.device.device_id] = state
        return result

    async def async_send_command(
        self,
        device_id: str,
        command_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        body = {
            "commandType": command_type,
            "idempotencyKey": uuid4().hex,
            "payload": dict(payload or {}),
        }
        return _require_mapping(
            await self._request(
                "POST",
                f"/devices/{quote(device_id, safe='')}/commands",
                json=body,
            ),
            "command",
        )

    async def async_wait_for_command(
        self,
        command: Mapping[str, Any],
        *,
        wait_timeout: int = COMMAND_TIMEOUT_SECONDS,
    ) -> Mapping[str, Any]:
        status = str(command.get("status") or "").upper()
        if status in FAILED_COMMAND_STATUSES:
            self._raise_command_error(command)
        if status == "SUCCESS":
            return command
        command_id = command.get("commandId")
        if not command_id:
            raise GendomeCommandError("Cloud response does not contain commandId")

        deadline = asyncio.get_running_loop().time() + wait_timeout
        current = command
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(COMMAND_POLL_INTERVAL_SECONDS)
            current = _require_mapping(
                await self._request(
                    "GET", f"/commands/{quote(str(command_id), safe='')}"
                ),
                "command status",
            )
            status = str(current.get("status") or "").upper()
            if status in TERMINAL_COMMAND_STATUSES:
                if status in FAILED_COMMAND_STATUSES:
                    self._raise_command_error(current)
                return current
        raise GendomeCommandError(
            "Timed out waiting for the device command",
            code="COMMAND_TIMEOUT",
        )

    async def async_send_and_wait(
        self,
        device_id: str,
        command_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        command = await self.async_send_command(device_id, command_type, payload)
        return await self.async_wait_for_command(command)

    async def async_get_charging_schedule(self, device_id: str) -> Mapping[str, Any]:
        return _require_mapping(
            await self._request(
                "GET", f"/devices/{quote(device_id, safe='')}/schedule/charging"
            ),
            "charging schedule",
        )

    async def async_set_charging_schedule_enabled(
        self, device_id: str, enabled: bool
    ) -> Mapping[str, Any]:
        return _require_mapping(
            await self._request(
                "PUT",
                f"/devices/{quote(device_id, safe='')}/schedule/charging/enabled",
                json={"enabled": enabled},
            ),
            "charging schedule",
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{OPENAPI_PREFIX}{path}"
        attempts = 2 if method.upper() == "GET" else 1
        for attempt in range(attempts):
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                    response = await self._requester.async_request(
                        method, url, **kwargs
                    )
                    return await self._decode_response(response)
            except (GendomeAuthError, GendomePermissionError, GendomeRateLimitError):
                raise
            except GendomeApiError as err:
                if attempt + 1 >= attempts or not _is_server_error(err.code):
                    raise
            except (TimeoutError, ClientError) as err:
                if attempt + 1 >= attempts:
                    self._remember_error("CONNECTION_ERROR", str(err), url)
                    raise GendomeConnectionError(
                        "Unable to communicate with Gendome Cloud"
                    ) from err
            await asyncio.sleep(0.5)
        raise GendomeConnectionError("Unable to communicate with Gendome Cloud")

    async def _decode_response(self, response: ClientResponse) -> Any:
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        try:
            payload = await response.json(content_type=None)
        except (json.JSONDecodeError, UnicodeDecodeError, ClientResponseError) as err:
            payload = None
            if response.status < 400:
                raise GendomeApiError("Cloud response is not valid JSON") from err

        message = _response_message(payload) or response.reason or "Gendome API error"
        code = _response_code(payload)
        if response.status == 401:
            self._remember_error(code or "UNAUTHORIZED", message, str(response.url))
            raise GendomeAuthError(message, code=code)
        if response.status == 403:
            self._remember_error(code or "FORBIDDEN", message, str(response.url))
            raise GendomePermissionError(message, code=code)
        if response.status == 429:
            self._remember_error("RATE_LIMITED", message, str(response.url))
            raise GendomeRateLimitError(message, retry_after=retry_after)
        if response.status >= 400:
            self._remember_error(
                code or str(response.status), message, str(response.url)
            )
            raise GendomeApiError(message, code=code or str(response.status))

        if isinstance(payload, Mapping) and "success" in payload:
            if not payload.get("success"):
                self._remember_error(code, message, str(response.url))
                if _looks_like_permission_error(code, message):
                    raise GendomePermissionError(message, code=code)
                if _looks_like_auth_error(code, message):
                    raise GendomeAuthError(message, code=code)
                if _looks_like_rate_error(code, message):
                    raise GendomeRateLimitError(message, retry_after=retry_after)
                raise GendomeApiError(message, code=code)
            self.last_error = None
            return payload.get("data")
        self.last_error = None
        return payload

    def _raise_command_error(self, command: Mapping[str, Any]) -> None:
        code = str(
            command.get("errorCode")
            or command.get("status")
            or "COMMAND_FAILED"
        )
        message = str(command.get("message") or f"Device command failed: {code}")
        self._remember_error(code, message, "/commands")
        raise GendomeCommandError(message, code=code)

    def _remember_error(self, code: str | None, message: str, endpoint: str) -> None:
        self.last_error = {"code": code, "message": message, "endpoint": endpoint}


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GendomeApiError(f"Cloud {name} response is not an object")
    return value


def _response_message(payload: Any) -> str | None:
    if isinstance(payload, Mapping):
        value = payload.get("message")
        return str(value) if value else None
    return None


def _response_code(payload: Any) -> str | None:
    if isinstance(payload, Mapping):
        value = payload.get("code")
        return str(value) if value is not None else None
    return None


def _parse_retry_after(value: str | None) -> int:
    try:
        return max(1, int(value or "60"))
    except ValueError:
        return 60


def _looks_like_auth_error(code: str | None, message: str) -> bool:
    text = f"{code or ''} {message}".lower()
    return (
        code == "401"
        or "token" in text
        or "unauthor" in text
        or "授权失效" in text
    )


def _looks_like_permission_error(code: str | None, message: str) -> bool:
    text = f"{code or ''} {message}".lower()
    return (
        code == "403"
        or "scope" in text
        or "permission" in text
        or "权限" in text
        or "授权范围" in text
    )


def _looks_like_rate_error(code: str | None, message: str) -> bool:
    text = f"{code or ''} {message}".lower()
    return code == "429" or "too many" in text or "频繁" in text


def _is_server_error(code: str | None) -> bool:
    try:
        return int(code or "0") >= 500
    except ValueError:
        return False
