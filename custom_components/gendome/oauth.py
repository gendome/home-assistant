"""OAuth implementations used by the Gendome integration."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import TYPE_CHECKING

from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    AUTHORIZE_URL,
    PUBLIC_OAUTH_CLIENT_ID,
    PUBLIC_OAUTH_IMPLEMENTATION,
    TOKEN_URL,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


class GendomePublicOAuth2Implementation(
    config_entry_oauth2_flow.LocalOAuth2Implementation
):
    """Authorization Code implementation for the public Gendome PKCE client."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Create a flow-scoped implementation and its PKCE verifier."""
        super().__init__(
            hass,
            PUBLIC_OAUTH_IMPLEMENTATION,
            PUBLIC_OAUTH_CLIENT_ID,
            "",
            AUTHORIZE_URL,
            TOKEN_URL,
        )
        # 96 random bytes encode to 128 URL-safe characters, which is within
        # RFC 7636's required 43..128 character verifier range.
        self.code_verifier = secrets.token_urlsafe(96)

    @property
    def name(self) -> str:
        """Return the user-facing implementation name."""
        return "Gendome"

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Add the S256 PKCE challenge to the authorization request."""
        digest = hashlib.sha256(self.code_verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return {
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

    @property
    def extra_token_resolve_data(self) -> dict[str, str]:
        """Add the matching PKCE verifier to the authorization-code exchange."""
        return {"code_verifier": self.code_verifier}


def create_public_oauth2_implementation(
    hass: HomeAssistant,
) -> GendomePublicOAuth2Implementation:
    """Create a fresh public implementation for a config or refresh flow."""
    return GendomePublicOAuth2Implementation(hass)


async def async_get_entry_oauth2_implementation(
    hass: HomeAssistant, entry: ConfigEntry
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return Gendome's production public OAuth implementation."""
    return create_public_oauth2_implementation(hass)
