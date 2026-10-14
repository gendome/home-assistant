"""Tests for the Java ApiResult envelope and error mapping."""

from typing import Any

import pytest

from custom_components.gendome.api import (
    GendomeApiClient,
    GendomeAuthError,
    GendomePermissionError,
    GendomeRateLimitError,
)


class FakeResponse:
    def __init__(
        self,
        payload: Any,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._payload = payload
        self.status = status
        self.headers = headers or {}
        self.reason = "test"
        self.url = "https://api.gendome.cloud/test"

    async def json(self, content_type=None) -> Any:
        return self._payload


class FakeRequester:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def async_request(self, method: str, url: str, **kwargs: Any):
        return self.response


@pytest.mark.asyncio
async def test_unwraps_successful_api_result() -> None:
    client = GendomeApiClient(
        FakeRequester(
            FakeResponse(
                {
                    "success": True,
                    "code": "200",
                    "message": "success",
                    "data": {"userId": "123", "region": "GLOBAL"},
                }
            )
        )
    )

    profile = await client.async_get_profile()

    assert profile.user_id == "123"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "exception"),
    [(401, GendomeAuthError), (403, GendomePermissionError)],
)
async def test_maps_http_auth_errors(status, exception) -> None:
    client = GendomeApiClient(
        FakeRequester(FakeResponse({"message": "denied"}, status=status))
    )

    with pytest.raises(exception):
        await client.async_get_profile()


@pytest.mark.asyncio
async def test_maps_retry_after_on_rate_limit() -> None:
    client = GendomeApiClient(
        FakeRequester(
            FakeResponse(
                {"message": "slow down"},
                status=429,
                headers={"Retry-After": "75"},
            )
        )
    )

    with pytest.raises(GendomeRateLimitError) as error:
        await client.async_get_devices()

    assert error.value.retry_after == 75


@pytest.mark.asyncio
async def test_maps_api_result_scope_error() -> None:
    client = GendomeApiClient(
        FakeRequester(
            FakeResponse(
                {
                    "success": False,
                    "code": "403",
                    "message": "缺少授权范围：device:control:switch",
                }
            )
        )
    )

    with pytest.raises(GendomePermissionError):
        await client.async_get_devices()
