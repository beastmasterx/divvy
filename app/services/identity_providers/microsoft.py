"""
Microsoft Entra ID (formerly Azure AD) OAuth2/OIDC provider implementation.
"""

import logging
from urllib.parse import urlencode

import httpx

from app.core.config import (
    get_microsoft_client_id,
    get_microsoft_client_secret,
    get_microsoft_redirect_uri,
    get_microsoft_tenant_id,
)
from app.exceptions import UnauthorizedError
from app.models import IdentityProvider as IdentityProviderEnum
from app.services.identity_providers.base import IdentityProviderTokenResponse, IdentityProviderUserInfo

logger = logging.getLogger(__name__)


class MicrosoftProvider:
    """Microsoft Entra ID (Microsoft Identity Platform) OAuth2/OIDC provider."""

    AUTHORIZATION_ENDPOINT = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
    TOKEN_ENDPOINT = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    USERINFO_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

    def __init__(self):
        """Initialize Microsoft provider with configuration."""
        self._client_id = get_microsoft_client_id()
        self._client_secret = get_microsoft_client_secret()
        self._tenant_id = get_microsoft_tenant_id()
        self._redirect_uri = get_microsoft_redirect_uri()

    @property
    def name(self) -> str:
        """Provider name."""
        return IdentityProviderEnum.MICROSOFT.value

    def get_authorization_url(self, state: str | None = None) -> str:
        """Generate Microsoft OAuth2 authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for redirecting user to Microsoft login
        """
        params: dict[str, str] = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": self._redirect_uri,
            "response_mode": "query",
            "scope": "openid profile email User.Read",
        }
        if state:
            params["state"] = state

        endpoint = self.AUTHORIZATION_ENDPOINT.format(tenant=self._tenant_id)
        return f"{endpoint}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> IdentityProviderTokenResponse:
        """Exchange authorization code for access token and ID token.

        Args:
            code: Authorization code from Microsoft callback

        Returns:
            TokenResponse containing standardized OAuth2 token data

        Raises:
            UnauthorizedError: If token exchange fails
        """
        endpoint = self.TOKEN_ENDPOINT.format(tenant=self._tenant_id)

        data: dict[str, str] = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, data=data)
                response.raise_for_status()
                raw_response = response.json()
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"Failed to exchange Microsoft authorization code: {error_detail}")
            raise UnauthorizedError("Failed to exchange authorization code with Microsoft") from e
        except httpx.RequestError as e:
            logger.error(f"Network error exchanging Microsoft code: {e}")
            raise UnauthorizedError("Network error during token exchange") from e

        return IdentityProviderTokenResponse(
            access_token=raw_response.get("access_token", ""),
            token_type=raw_response.get("token_type", "Bearer"),
            expires_in=raw_response.get("expires_in"),
            refresh_token=raw_response.get("refresh_token"),
            scope=raw_response.get("scope"),
            id_token=raw_response.get("id_token"),
            raw_data=raw_response,
        )

    async def get_user_info(self, access_token: str) -> IdentityProviderUserInfo:
        """Get and extract standardized user information from Microsoft Graph API.

        Args:
            access_token: Microsoft access token

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
            logger.error(f"Failed to get Microsoft user info: {error_detail}")
            raise UnauthorizedError("Failed to retrieve user information from Microsoft") from e
        except httpx.RequestError as e:
            logger.error(f"Network error getting Microsoft user info: {e}")
            raise UnauthorizedError("Network error retrieving user information") from e

        external_id = raw_response.get("id") or raw_response.get("objectId", "")
        email = raw_response.get("mail") or raw_response.get("userPrincipalName", "")
        name = raw_response.get("displayName")

        if not external_id:
            raise UnauthorizedError("Could not extract user ID from Microsoft response")
        if not email:
            raise UnauthorizedError("Could not extract email from Microsoft response")

        return IdentityProviderUserInfo(
            external_id=external_id,
            email=email,
            name=name,
            raw_data=raw_response,
        )
