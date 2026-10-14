"""Tests for the fixed production endpoints and requested permissions."""

from custom_components.gendome.const import (
    DEFAULT_API_BASE_URL,
    DEFAULT_OAUTH_BASE_URL,
    ENVIRONMENT,
    ENVIRONMENT_PROD,
    OAUTH_SCOPE,
    OAUTH_SCOPES,
    REVOKE_URL,
)


def test_integration_uses_only_production_services() -> None:
    assert ENVIRONMENT == ENVIRONMENT_PROD
    assert DEFAULT_API_BASE_URL == "https://api.gendome.cloud"
    assert DEFAULT_OAUTH_BASE_URL == "https://oauth.gendome.cloud"


def test_oauth_scope_contains_only_supported_v1_permissions() -> None:
    assert " ".join(OAUTH_SCOPES) == OAUTH_SCOPE
    assert set(OAUTH_SCOPES) == {
        "device:read",
        "statistics:read",
        "device:control:switch",
        "device:control:setting",
        "scheduled_charging:read",
        "scheduled_charging:write",
    }


def test_revoke_endpoint_uses_production_oauth_service() -> None:
    assert REVOKE_URL.startswith(DEFAULT_OAUTH_BASE_URL)
    assert REVOKE_URL.endswith("/oauth/revokeToken")
