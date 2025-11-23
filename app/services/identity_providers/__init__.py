"""
Identity provider implementations for OAuth2/OIDC authentication.
"""

from .base import IdentityProvider, TokenResponse, UserInfo
from .google import GoogleProvider
from .microsoft import MicrosoftProvider
from .registry import IdentityProviderRegistry

__all__ = [
    "IdentityProvider",
    "TokenResponse",
    "UserInfo",
    "GoogleProvider",
    "MicrosoftProvider",
    "IdentityProviderRegistry",
]
