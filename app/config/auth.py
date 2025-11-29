"""
Authentication Configuration 🔒

This module defines all configuration related to internal security (JWT)
and external Identity Providers (OAuth credentials).

All duration getters return `datetime.timedelta` objects for type clarity.
"""

import os
from datetime import timedelta

# --- JWT TOKEN CONFIGURATION ---


def get_jwt_algorithm() -> str:
    """
    Get the JWT signing algorithm from the environment or use the default.

    Returns:
        The algorithm string (default: "HS256").
    """
    return os.getenv("DIVVY_JWT_ALGORITHM", "HS256")


def get_jwt_secret_key() -> str:
    """
    Get JWT secret key from environment variable.

    Returns:
        JWT secret key string.

    Raises:
        ValueError: If DIVVY_JWT_SECRET_KEY is not set or is too short (less than 32 chars).
    """
    secret_key = os.getenv("DIVVY_JWT_SECRET_KEY")
    if not secret_key:
        raise ValueError("DIVVY_JWT_SECRET_KEY environment variable is required")
    if len(secret_key) < 32:
        raise ValueError("DIVVY_JWT_SECRET_KEY must be at least 32 characters long")
    return secret_key


def get_jwt_access_token_expire_delta() -> timedelta:
    """
    Get JWT access token expiration time as a timedelta object.

    The duration is read in minutes from the environment (DIVVY_JWT_ACCESS_TOKEN_EXPIRE_MINUTES).
    Returns:
        Expiration time (default: 30 minutes).
    """
    minutes = int(os.getenv("DIVVY_JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    return timedelta(minutes=minutes)


def get_jwt_refresh_token_expire_delta() -> timedelta:
    """
    Get JWT refresh token expiration time as a timedelta object.

    The duration is read in days from the environment (DIVVY_JWT_REFRESH_TOKEN_EXPIRE_DAYS).
    Returns:
        Expiration time (default: 7 days).
    """
    days = int(os.getenv("DIVVY_JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    return timedelta(days=days)


def get_account_link_request_expiration_delta() -> timedelta:
    """
    Get account link request expiration time as a timedelta object.

    The duration is read in hours from the environment (DIVVY_ACCOUNT_LINK_REQUEST_EXPIRATION_HOURS).
    Returns:
        Expiration time (default: 24 hours).
    """
    hours = int(os.getenv("DIVVY_ACCOUNT_LINK_REQUEST_EXPIRATION_HOURS", "24"))
    return timedelta(hours=hours)


# --- IDENTITY PROVIDER (OAuth) CONFIGURATION ---


def get_microsoft_client_id() -> str:
    """Get Microsoft Entra ID Client ID."""
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    if not client_id:
        raise ValueError("MICROSOFT_CLIENT_ID environment variable is required")
    return client_id


def get_microsoft_client_secret() -> str:
    """Get Microsoft Entra ID Client Secret."""
    client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
    if not client_secret:
        raise ValueError("MICROSOFT_CLIENT_SECRET environment variable is required")
    return client_secret


def get_microsoft_tenant_id() -> str:
    """Get Microsoft Entra ID Tenant ID (or 'common' for multi-tenant)."""
    return os.getenv("MICROSOFT_TENANT_ID", "common")


def get_google_client_id() -> str:
    """Get Google OAuth2 Client ID."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
    return client_id


def get_google_client_secret() -> str:
    """Get Google OAuth2 Client Secret."""
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_secret:
        raise ValueError("GOOGLE_CLIENT_SECRET environment variable is required")
    return client_secret
