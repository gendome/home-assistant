"""Tests for the built-in public OAuth client and PKCE config flow."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.gendome import config_flow as config_flow_module
from custom_components.gendome.config_flow import GendomeConfigFlow
from custom_components.gendome.const import (
    OAUTH_SCOPE,
    PUBLIC_OAUTH_CLIENT_ID,
    PUBLIC_OAUTH_IMPLEMENTATION,
)
from custom_components.gendome.oauth import (
    GendomePublicOAuth2Implementation,
    async_get_entry_oauth2_implementation,
)


def _fake_hass():
    """Return the small Home Assistant surface needed by the OAuth helper."""
    return SimpleNamespace(
        data={},
        config=SimpleNamespace(components={"my"}),
    )


def test_manifest_requires_my_for_a_fixed_https_callback() -> None:
    """The My integration keeps the public client's redirect URI stable."""
    manifest_path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "gendome"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert "my" in manifest["dependencies"]


@pytest.mark.asyncio
async def test_public_authorize_url_uses_client_scope_and_s256_pkce() -> None:
    """The browser request contains public-client and PKCE parameters."""
    flow = GendomeConfigFlow()
    flow.hass = _fake_hass()
    flow.flow_id = "flow-id"
    flow.flow_impl = GendomePublicOAuth2Implementation(flow.hass)

    url = await flow.async_generate_authorize_url()
    query = parse_qs(urlsplit(url).query)

    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(flow.flow_impl.code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    assert query["client_id"] == [PUBLIC_OAUTH_CLIENT_ID]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == [
        "https://my.home-assistant.io/redirect/oauth"
    ]
    assert query["scope"] == [OAUTH_SCOPE]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [expected_challenge]
    assert "client_secret" not in query


@pytest.mark.asyncio
async def test_code_exchange_uses_matching_verifier(monkeypatch) -> None:
    """The authorization-code exchange sends the verifier for this flow."""
    implementation = GendomePublicOAuth2Implementation(_fake_hass())
    token_request = AsyncMock(
        return_value={"access_token": "token", "expires_in": 3600}
    )
    monkeypatch.setattr(implementation, "_token_request", token_request)

    await implementation.async_resolve_external_data(
        {
            "code": "one-time-code",
            "state": {"redirect_uri": "https://my.home-assistant.io/redirect/oauth"},
        }
    )

    token_request.assert_awaited_once_with(
        {
            "grant_type": "authorization_code",
            "code": "one-time-code",
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
            "code_verifier": implementation.code_verifier,
        }
    )


@pytest.mark.asyncio
async def test_public_token_request_never_sends_a_secret(monkeypatch) -> None:
    """The public token endpoint call uses form client ID and no Basic secret."""
    response = SimpleNamespace(
        status=200,
        raise_for_status=Mock(),
        json=AsyncMock(return_value={"access_token": "token", "expires_in": 3600}),
    )
    session = SimpleNamespace(post=AsyncMock(return_value=response))
    monkeypatch.setattr(
        config_flow_module.config_entry_oauth2_flow,
        "async_get_clientsession",
        lambda _hass: session,
    )
    implementation = GendomePublicOAuth2Implementation(_fake_hass())

    await implementation._token_request(
        {"grant_type": "refresh_token", "refresh_token": "refresh-token"}
    )

    session.post.assert_awaited_once()
    request_data = session.post.await_args.kwargs["data"]
    assert request_data["client_id"] == PUBLIC_OAUTH_CLIENT_ID
    assert "client_secret" not in request_data
    assert "auth" not in session.post.await_args.kwargs


@pytest.mark.asyncio
async def test_normal_user_flow_skips_implementation_picker(monkeypatch) -> None:
    """Normal HACS setup always starts a fresh public PKCE implementation."""
    first_flow = GendomeConfigFlow()
    first_flow.hass = _fake_hass()
    first_flow.async_step_auth = AsyncMock(return_value={"type": "external"})
    second_flow = GendomeConfigFlow()
    second_flow.hass = _fake_hass()
    second_flow.async_step_auth = AsyncMock(return_value={"type": "external"})

    result = await first_flow.async_step_user()
    await second_flow.async_step_user()

    assert result == {"type": "external"}
    assert first_flow.flow_impl.domain == PUBLIC_OAUTH_IMPLEMENTATION
    assert first_flow.flow_impl.client_id == PUBLIC_OAUTH_CLIENT_ID
    assert first_flow.flow_impl.client_secret == ""
    assert first_flow.flow_impl.code_verifier != second_flow.flow_impl.code_verifier
    first_flow.async_step_auth.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_normal_user_flow_returns_direct_browser_redirect(monkeypatch) -> None:
    """Starting setup returns the Gendome authorize URL in one HA step."""
    flow = GendomeConfigFlow()
    flow.hass = _fake_hass()
    flow.flow_id = "flow-id"

    result = await flow.async_step_user()

    assert result["type"] is FlowResultType.EXTERNAL_STEP
    assert result["step_id"] == "auth"
    assert urlsplit(result["url"]).netloc == "oauth.gendome.cloud"
    assert parse_qs(urlsplit(result["url"]).query)["client_id"] == [
        PUBLIC_OAUTH_CLIENT_ID
    ]


@pytest.mark.asyncio
async def test_public_entry_resolves_after_restart() -> None:
    """A public config entry remains loadable after Home Assistant restarts."""
    entry = SimpleNamespace(
        data={"auth_implementation": PUBLIC_OAUTH_IMPLEMENTATION}
    )

    implementation = await async_get_entry_oauth2_implementation(
        _fake_hass(), entry
    )

    assert isinstance(implementation, GendomePublicOAuth2Implementation)
    assert implementation.domain == PUBLIC_OAUTH_IMPLEMENTATION
