"""
Identity provider implementations for OAuth2/OIDC authentication.
"""

from .google import GoogleProvider
from .microsoft import MicrosoftProvider
from .protocol import IdentityProvider, IdentityProviderTokenResponse, IdentityProviderUserInfo
from .registry import IdentityProviderRegistry

__all__ = [
    "IdentityProvider",
    "IdentityProviderTokenResponse",
    "IdentityProviderUserInfo",
    "GoogleProvider",
    "MicrosoftProvider",
    "IdentityProviderRegistry",
]
