"""
API v1 router for authentication endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status

from app.api.dependencies import get_auth_service, get_current_user
from app.api.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse
from app.exceptions import UnauthorizedError
from app.models import User
from app.services import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    http: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Register a new user account.

    Creates a new user with the provided email, name, and password.
    Returns a JWT access token and refresh token upon successful registration.

    Args:
        request: Registration request containing email, name, and password
        http: HTTP request object for extracting device info
        auth: Authentication service instance

    Returns:
        TokenResponse containing access token and refresh token

    Raises:
        ConflictError: If email already exists (raised by auth_service)
    """
    device_info = _get_device_info(http)
    return auth.register(
        email=request.email,
        name=request.name,
        password=request.password,
        device_info=device_info,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    http: Request,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate a user and return a JWT access token and refresh token.

    Validates the user's email and password, then returns tokens
    if authentication succeeds.

    Args:
        request: Login request containing email and password
        http: HTTP request object for extracting device info
        auth: Authentication service instance

    Returns:
        TokenResponse containing access token and refresh token

    Raises:
        UnauthorizedError: If credentials are invalid
    """
    device_info = _get_device_info(http)
    return auth.authenticate(request.email, request.password, device_info)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: RefreshTokenRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Refresh an access token using a refresh token.

    Validates the refresh token, rotates it (invalidates old, creates new),
    and returns a new access token and refresh token.

    Args:
        request: Refresh token request containing the refresh token
        auth: Authentication service instance

    Returns:
        TokenResponse containing new access token and refresh token

    Raises:
        UnauthorizedError: If refresh token is invalid, expired, or revoked
    """
    return auth.rotate_refresh_token(request.refresh_token)


@router.post("/logout", response_model=None)
def logout(
    refresh_token: Annotated[str | None, Header(alias="X-Refresh-Token")] = None,
    auth: AuthService = Depends(get_auth_service),
) -> None:
    """
    Logout from a single device by revoking the refresh token.

    Requires X-Refresh-Token header with the refresh token to revoke.

    Args:
        refresh_token: Refresh token from X-Refresh-Token header
        auth: Authentication service instance

    Raises:
        UnauthorizedError: If refresh token is invalid or missing
    """
    if not refresh_token:
        raise UnauthorizedError("X-Refresh-Token header is required")
    auth.revoke_refresh_token(refresh_token)


@router.post("/logout-all", response_model=None)
def logout_all(
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> None:
    """
    Logout from all devices by revoking all refresh tokens for the authenticated user.

    Requires Authorization header with valid access token.

    Args:
        user: Current authenticated user from access token
        auth: Authentication service instance
    """
    auth.revoke_all_user_refresh_tokens(user.id)


def _get_device_info(http: Request) -> str:
    return http.headers.get("User-Agent", "Unknown")
