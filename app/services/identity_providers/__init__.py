"""
Identity provider implementations for OAuth2/OIDC authentication.
"""

from .base import IdentityProvider, IdentityProviderTokenResponse, IdentityProviderUserInfo
from .google import GoogleProvider
from .microsoft import MicrosoftProvider
from .registry import IdentityProviderRegistry

__all__ = [
    "IdentityProvider",
    "IdentityProviderTokenResponse",
    "IdentityProviderUserInfo",
    "GoogleProvider",
    "MicrosoftProvider",
    "IdentityProviderRegistry",
]
