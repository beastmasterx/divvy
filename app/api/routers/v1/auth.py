"""
API v1 router for authentication endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, status

from app.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_user_optional,
    get_identity_provider_service,
)
from app.api.schemas import UserResponse
from app.api.schemas.auth import (
    AccountLinkVerifyRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackResponse,
    RegisterRequest,
    TokenResponse,
)
from app.exceptions import ValidationError
from app.models import User
from app.services import AuthService
from app.services.identity_provider import IdentityProviderService

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


@router.post("/token", response_model=TokenResponse)
def token(
    http: Request,
    grant_type: Annotated[str, Form()] = "password",
    username: Annotated[str | None, Form()] = None,
    password: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    OAuth2 token endpoint - issue and refresh access tokens (RFC 6749).

    Supports two grant types:
    - password: Authenticate with username and password
    - refresh_token: Exchange refresh token for new access token

    Args:
        http: HTTP request object for extracting device info
        grant_type: OAuth2 grant type ("password" or "refresh_token")
        username: User email (required for password grant)
        password: User password (required for password grant)
        refresh_token: Refresh token (required for refresh_token grant)
        auth: Authentication service instance

    Returns:
        TokenResponse containing access token and refresh token

    Raises:
        ValidationError: If grant_type is invalid or required parameters are missing
        UnauthorizedError: If credentials are invalid or refresh token is invalid/expired
    """
    device_info = _get_device_info(http)

    if grant_type == "password":
        if not username or not password:
            raise ValidationError("username and password are required for password grant")
        return auth.authenticate(username, password, device_info)

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise ValidationError("refresh_token is required for refresh_token grant")
        return auth.rotate_refresh_token(refresh_token)

    else:
        raise ValidationError(f"Unsupported grant_type: {grant_type}. Supported types: password, refresh_token")


@router.post("/revoke", response_model=None)
def revoke_token(
    token: Annotated[str, Form()],
    token_type_hint: Annotated[str | None, Form()] = None,
    auth: AuthService = Depends(get_auth_service),
) -> None:
    """
    OAuth2 token revocation endpoint (RFC 7009).

    Revokes a refresh token. Note: This implementation only supports revoking refresh tokens.
    Access tokens are stateless JWTs and cannot be revoked/blacklisted in this system.

    Args:
        token: Refresh token to revoke (OAuth2 standard form parameter, required)
        token_type_hint: Hint about the token type (accepted but only "refresh_token" is supported)
        auth: Authentication service instance

    Raises:
        ValidationError: If token is not provided
        UnauthorizedError: If token is invalid

    Note:
        Access tokens cannot be revoked in this implementation as they are stateless JWTs.
        To invalidate access tokens, revoke the associated refresh token and wait for
        the access token to expire naturally.
    """
    # Only refresh tokens can be revoked in this implementation
    auth.revoke_refresh_token(token)


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


@router.get("/oauth/{provider}/authorize", response_model=OAuthAuthorizeResponse)
def oauth_authorize(
    provider: str,
    state: Annotated[str | None, Query()] = None,
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> OAuthAuthorizeResponse:
    """
    Initiate OAuth flow by redirecting to identity provider.

    Returns the authorization URL that the client should redirect the user to.
    The user will authenticate with the provider and be redirected back to the callback endpoint.

    Args:
        provider: Identity provider name (e.g., 'microsoft', 'google')
        state: Optional state parameter for CSRF protection
        identity_provider_service: Identity provider service instance

    Returns:
        OAuthAuthorizeResponse containing the authorization URL

    Raises:
        ValueError: If provider is not registered
    """
    authorization_url = identity_provider_service.get_authorization_url(provider, state)
    return OAuthAuthorizeResponse(authorization_url=authorization_url)


@router.get("/oauth/{provider}/callback", response_model=OAuthCallbackResponse | TokenResponse)
async def oauth_callback(
    provider: str,
    code: Annotated[str, Query(..., description="Authorization code from OAuth provider")],
    state: Annotated[str | None, Query()] = None,
    http: Request = None,  # type: ignore[assignment]
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> OAuthCallbackResponse | TokenResponse:
    """
    Handle OAuth callback from identity provider.

    Exchanges the authorization code for tokens and either:
    - Returns tokens if user is authenticated (new account or existing linked account)
    - Returns account linking info if email already exists (requires password verification)

    Args:
        provider: Identity provider name (e.g., 'microsoft', 'google')
        code: Authorization code from OAuth provider
        state: Optional state parameter (should match the one sent in authorize)
        http: HTTP request object for extracting device info
        identity_provider_service: Identity provider service instance

    Returns:
        TokenResponse if authenticated, or OAuthCallbackResponse if linking required

    Raises:
        ValueError: If provider is not registered
        UnauthorizedError: If OAuth flow fails
    """
    device_info = _get_device_info(http) if http else None
    result = await identity_provider_service.handle_oauth_callback(provider, code, state, device_info)

    # If result is a dict, it means linking is required
    if isinstance(result, dict):
        return OAuthCallbackResponse(**result)

    # Otherwise, it's a TokenResponse
    return result


@router.post("/link/verify", status_code=status.HTTP_204_NO_CONTENT)
def verify_account_link(
    request: AccountLinkVerifyRequest,
    current_user: UserResponse | None = Depends(get_current_user_optional),
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> None:
    """
    Verify an account link request with password (without approving).

    This endpoint allows the client to verify the password before showing
    the approval UI. The actual linking happens in the approve endpoint.

    If the user is already authenticated, password is not required.

    Args:
        request: Account link verification request with token and optional password
        current_user: Current authenticated user (optional)
        identity_provider_service: Identity provider service instance

    Raises:
        NotFoundError: If request not found
        ValidationError: If request is expired or already processed, or if password is required but not provided
        UnauthorizedError: If password is incorrect or authenticated user doesn't match request
    """
    authenticated_user_id = current_user.id if current_user else None
    identity_provider_service.verify_account_link_request(
        request.request_token, request.password, authenticated_user_id
    )


@router.post("/link/approve", response_model=TokenResponse)
def approve_account_link(
    request: AccountLinkVerifyRequest,
    current_user: UserResponse | None = Depends(get_current_user_optional),
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> TokenResponse:
    """
    Approve an account link request by verifying password or authenticated user and linking the identity.

    This endpoint verifies the password (or authenticated user) and then links the external identity
    to the existing user account. Returns tokens for the authenticated user.

    If the user is already authenticated, password is not required.

    Args:
        request: Account link approval request with token and optional password
        current_user: Current authenticated user (optional)
        identity_provider_service: Identity provider service instance

    Returns:
        TokenResponse with access and refresh tokens

    Raises:
        NotFoundError: If request not found
        ValidationError: If request is expired or already processed, or if password is required but not provided
        UnauthorizedError: If password is incorrect or authenticated user doesn't match request
    """
    authenticated_user_id = current_user.id if current_user else None
    return identity_provider_service.approve_account_link_request(
        request.request_token, request.password, authenticated_user_id
    )


def _get_device_info(http: Request) -> str:
    return http.headers.get("User-Agent", "Unknown")
