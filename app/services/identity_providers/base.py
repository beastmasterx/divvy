"""
Base abstraction for identity providers.
"""

from typing import Any, NamedTuple, Protocol


class TokenResponse(NamedTuple):
    """OAuth2 token response from identity provider."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None
    raw_data: dict[str, Any] | None = None


class UserInfo(NamedTuple):
    """Standardized user information from identity provider."""

    external_id: str
    email: str
    name: str | None = None
    raw_data: dict[str, Any] | None = None


class IdentityProvider(Protocol):
    """Protocol/interface for identity providers."""

    @property
    def name(self) -> str:
        """Provider name (e.g., 'microsoft', 'google')."""
        ...

    def get_authorization_url(self, state: str | None = None) -> str:
        """Generate OAuth2 authorization URL.

        Args:
            state: Optional CSRF protection state parameter

        Returns:
            Authorization URL for redirecting user to provider login
        """
        ...

    async def exchange_code_for_tokens(self, code: str) -> TokenResponse:
        """Exchange authorization code for access token and ID token.

        Args:
            code: Authorization code from provider callback

        Returns:
            TokenResponse containing standardized OAuth2 token data

        Raises:
            UnauthorizedError: If token exchange fails
        """
        ...

    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get and extract standardized user information from provider's API.

        Args:
            access_token: Provider access token

        Returns:
            UserInfo containing standardized user data (external_id, email, name)

        Raises:
            UnauthorizedError: If API call fails or required fields cannot be extracted
        """
        ...
