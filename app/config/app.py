"""
Application Configuration 🌐

This module defines general, non-secret application settings, primarily focusing
on routing and external URLs.
"""

import os

# --- APPLICATION URLS ---


def get_frontend_url() -> str:
    """
    Get frontend application URL.

    Used for OAuth redirect URIs and client-side routing.
    Returns:
        Frontend URL (default: http://localhost:3000)
    """
    return os.getenv("DIVVY_FRONTEND_URL", "http://localhost:3000")


# --- REDIRECT URIs (Dependent on Frontend URL) ---


def get_microsoft_redirect_uri() -> str:
    """
    Get OAuth redirect URI for Microsoft.

    Returns the frontend route that handles OAuth callbacks.
    """
    frontend_url = get_frontend_url()
    return f"{frontend_url}/auth/callback/microsoft"


def get_google_redirect_uri() -> str:
    """
    Get OAuth redirect URI for Google.

    Returns the frontend route that handles OAuth callbacks.
    """
    frontend_url = get_frontend_url()
    return f"{frontend_url}/auth/callback/google"
