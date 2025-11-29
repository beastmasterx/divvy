"""
Authentication (authn) Package 🔑

This package is dedicated to **Identity Provision**. It answers the question:
'Who is the user?'

It handles token validation, signature verification, and retrieving the base
User object. Functions here raise a 401 Unauthorized error on failure.

---
VERB CONVENTION: The 'get_current_' Family
The 'get_' prefix uses the **Imperative Command** style (e.g., 'Get the user').
It is reserved for **Identity Providers** that retrieve and return the authenticated
subject's data.

Contents:
    get_current_user: The primary dependency for retrieving an authenticated User
                      object from a request token.
    get_claims_payload: Utility function to decode and verify token claims.

"""

# Example exports to define the public interface
from .token_handlers import get_claims_payload
from .user_providers import get_current_user

__all__ = [
    "get_current_user",
    "get_claims_payload",
]
