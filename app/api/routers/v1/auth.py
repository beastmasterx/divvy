"""
API v1 router for authentication endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import Discriminator

from app.api.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_user_optional,
    get_identity_provider_service,
)
from app.exceptions import ValidationError
from app.models import User
from app.schemas import UserResponse
from app.schemas.auth import (
    AccountLinkVerifyRequest,
    LinkingRequiredResponse,
    OAuthAuthorizeResponse,
    RegisterRequest,
    TokenResponse,
)
from app.services import AuthService
from app.services.identity_provider import IdentityProviderService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def register(
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
    return await auth.register(
        email=request.email,
        name=request.name,
        password=request.password,
        device_info=device_info,
    )


@router.post("/token", response_model=TokenResponse, response_model_exclude_none=True)
async def token(
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
        return await auth.authenticate(username, password, device_info)

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise ValidationError("refresh_token is required for refresh_token grant")
        return await auth.rotate_refresh_token(refresh_token)

    else:
        raise ValidationError(f"Unsupported grant_type: {grant_type}. Supported types: password, refresh_token")


@router.post("/revoke", response_model=None)
async def revoke_token(
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
    await auth.revoke_refresh_token(token)


@router.post("/logout-all", response_model=None)
async def logout_all(
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
    await auth.revoke_all_user_refresh_tokens(user.id)


@router.get("/oauth/{provider}/authorize")
def oauth_authorize(
    provider: str,
    state: Annotated[str | None, Query()] = None,
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> RedirectResponse:
    """
    Initiate OAuth flow by redirecting to identity provider.

    This endpoint starts the OAuth2 Authorization Code flow. It redirects the user
    to the identity provider's authorization page where they authenticate, then the
    provider redirects back to our callback endpoint.

    OAuth Flow Overview:
    ===================
    1. Client calls this endpoint (GET /oauth/{provider}/authorize)
       - Optional: Include `state` parameter for CSRF protection
       - State can be:
         * Frontend-generated random string (login flow): Frontend verifies on return
         * Backend-generated signed JWT token (link flow): Backend verifies on callback

    2. Backend redirects user to provider's authorization page (HTTP 302)
       - User authenticates with provider (Microsoft, Google, etc.)
       - Provider redirects back to: {frontend_url}/auth/callback/{provider}

    3. Frontend receives callback at /auth/callback/{provider}
       - Extracts `code` and `state` from query parameters
       - Calls backend: GET /oauth/{provider}/callback?code=...&state=...

    4. Backend handles callback (oauth_callback endpoint):
       - Exchanges authorization code for access token
       - Gets user info from provider
       - Determines flow based on state and existing accounts:
         a) Identity exists → Return tokens (user already linked)
         b) Signed state token with operation="link" → Directly link account (authenticated user)
         c) Email exists → Create link request (requires password verification)
         d) New user → Create account and identity, return tokens

    5. Client receives response:
       - TokenResponse: Authentication successful, contains access_token and refresh_token
       - LinkingRequiredResponse: Account linking required, contains request_token for approval

    State Parameter:
    ===============
    The state parameter serves different purposes depending on the flow:

    Login Flow (Frontend-Generated State):
    - Frontend generates random string (e.g., crypto.randomUUID())
    - Frontend stores state and verifies it matches on callback
    - Backend passes state through without verification
    - Purpose: CSRF protection

    Link Flow (Backend-Generated Signed State Token):
    - Backend creates signed JWT via create_state_token(operation="link", user_id=...)
    - Backend verifies token signature and expiration on callback
    - Token contains: operation="link", user_id, nonce, exp, iat
    - Purpose: Stateless context for authenticated account linking

    Args:
        provider: Identity provider name (e.g., 'microsoft', 'google')
        state: Optional state parameter for CSRF protection
            - Frontend-generated: Random string (frontend verifies)
            - Backend-generated: Signed JWT token (backend verifies)
        identity_provider_service: Identity provider service instance

    Returns:
        HTTP 302 redirect to OAuth provider authorization URL

    Raises:
        ValueError: If provider is not registered

    Example:
        # Login flow (frontend generates state)
        GET /oauth/microsoft/authorize?state=550e8400-e29b-41d4-a716-446655440000
        → Redirects to Microsoft login page

        # Link flow (backend generates signed state token)
        POST /link/microsoft/initiate (with auth token)
        → Returns authorization_url with signed state token
        → Frontend redirects to that URL
    """
    authorization_url = identity_provider_service.get_authorization_url(provider, state)
    return RedirectResponse(url=authorization_url)


@router.get(
    "/oauth/{provider}/callback",
    response_model=Annotated[
        TokenResponse | LinkingRequiredResponse,
        Discriminator("response_type"),
    ],
)
async def oauth_callback(
    provider: str,
    code: Annotated[str, Query(..., description="Authorization code from OAuth provider")],
    state: Annotated[str | None, Query()] = None,
    http: Request = None,  # type: ignore[assignment]
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> TokenResponse | LinkingRequiredResponse:
    """
    Handle OAuth callback from identity provider.

    Exchanges the authorization code for tokens and either:
    - Returns tokens if user is authenticated (new account or existing linked account)
    - Returns account linking info if email already exists (requires password verification)

    The response includes a `response_type` field that indicates which type of response:
    - `"token"`: Authentication succeeded, contains access_token and refresh_token
    - `"linking_required"`: Account linking required, contains request_token and email

    Args:
        provider: Identity provider name (e.g., 'microsoft', 'google')
        code: Authorization code from OAuth provider
        state: Optional state parameter (should match the one sent in authorize)
        http: HTTP request object for extracting device info
        identity_provider_service: Identity provider service instance

    Returns:
        TokenResponse (response_type="token") if authenticated,
        or LinkingRequiredResponse (response_type="linking_required") if linking required

    Raises:
        ValueError: If provider is not registered
        UnauthorizedError: If OAuth flow fails
    """
    device_info = _get_device_info(http) if http else None
    return await identity_provider_service.handle_oauth_callback(provider, code, state, device_info)


@router.post("/link/{provider}/initiate", response_model=OAuthAuthorizeResponse)
def initiate_account_link(
    provider: str,
    current_user: User = Depends(get_current_user),
    identity_provider_service: IdentityProviderService = Depends(get_identity_provider_service),
) -> OAuthAuthorizeResponse:
    """
    Initiate account linking for an authenticated user.

    Creates a signed state token with the user's ID and operation context,
    then returns the OAuth authorization URL that the client should redirect to.
    The state token ensures that when the OAuth callback returns, we know:
    - This is a link operation (not a login)
    - Which user is requesting the link

    Requires Authorization header with valid access token.

    Args:
        provider: Identity provider name (e.g., 'microsoft', 'google')
        current_user: Current authenticated user from access token
        identity_provider_service: Identity provider service instance

    Returns:
        OAuthAuthorizeResponse containing the authorization URL with signed state token

    Raises:
        ValueError: If provider is not registered
    """
    authorization_url = identity_provider_service.get_link_authorization_url(provider, current_user.id)
    return OAuthAuthorizeResponse(authorization_url=authorization_url)


@router.post("/link/approve", response_model=TokenResponse, response_model_exclude_none=True)
async def approve_account_link(
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
    return await identity_provider_service.approve_account_link_request(
        request.request_token, request.password, authenticated_user_id
    )


def _get_device_info(http: Request) -> str:
    return http.headers.get("User-Agent", "Unknown")
