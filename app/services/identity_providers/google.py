"""
Google OAuth2 provider implementation.
"""

import logging
from urllib.parse import urlencode

import httpx

from app.core.config import (
    get_google_client_id,
    get_google_client_secret,
    get_google_redirect_uri,
)
from app.exceptions import UnauthorizedError
from app.models import IdentityProvider as IdentityProviderEnum
from app.services.identity_providers.base import TokenResponse, UserInfo

logger = logging.getLogger(__name__)


class GoogleProvider:
    """Google OAuth2 provider."""

    AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
    USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        """Initialize Google provider with configuration."""
        self._client_id = get_google_client_id()
        self._client_secret = get_google_client_secret()
        self._redirect_uri = get_google_redirect_uri()

    @property
    def name(self) -> str:
        """Provider name."""
        return IdentityProviderEnum.GOOGLE.value

    def get_authorization_url(self, state: str | None = None) -> str:
        """Generate Google OAuth2 authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for redirecting user to Google login
        """
        params: dict[str, str] = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "scope": "openid profile email",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }
        if state:
            params["state"] = state

        return f"{self.AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> TokenResponse:
        """Exchange authorization code for access token and ID token.

        Args:
            code: Authorization code from Google callback

        Returns:
            TokenResponse containing standardized OAuth2 token data

        Raises:
            UnauthorizedError: If token exchange fails
        """
        data: dict[str, str] = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.TOKEN_ENDPOINT, data=data)
                response.raise_for_status()
                raw_response = response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to exchange Google authorization code: {error_detail}")
            raise UnauthorizedError("Failed to exchange authorization code with Google") from e
        except httpx.RequestError as e:
            logger.error(f"Network error exchanging Google code: {e}")
            raise UnauthorizedError("Network error during token exchange") from e

        return TokenResponse(
            access_token=raw_response.get("access_token", ""),
            token_type=raw_response.get("token_type", "Bearer"),
            expires_in=raw_response.get("expires_in"),
            refresh_token=raw_response.get("refresh_token"),
            scope=raw_response.get("scope"),
            id_token=raw_response.get("id_token"),
            raw_data=raw_response,
        )

    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get and extract standardized user information from Google UserInfo API.

        Args:
            access_token: Google access token

        Returns:
            UserInfo containing standardized user data (external_id, email, name)

        Raises:
            UnauthorizedError: If API call fails or required fields cannot be extracted
        """
        headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.USERINFO_ENDPOINT, headers=headers)
                response.raise_for_status()
                raw_response = response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to get Google user info: {error_detail}")
            raise UnauthorizedError("Failed to retrieve user information from Google") from e
        except httpx.RequestError as e:
            logger.error(f"Network error getting Google user info: {e}")
            raise UnauthorizedError("Network error retrieving user information") from e

        external_id = raw_response.get("id", "")
        email = raw_response.get("email", "")
        name = raw_response.get("name")

        if not external_id:
            raise UnauthorizedError("Could not extract user ID from Google response")
        if not email:
            raise UnauthorizedError("Could not extract email from Google response")

        return UserInfo(
            external_id=external_id,
            email=email,
            name=name,
            raw_data=raw_response,
        )
