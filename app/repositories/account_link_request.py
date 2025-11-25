"""
Repository for managing account link request entities.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AccountLinkRequest


class AccountLinkRequestRepository:
    """Repository for managing account link request entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_request_by_id(self, request_id: int) -> AccountLinkRequest | None:
        """Retrieve a specific account link request by its ID."""
        stmt = select(AccountLinkRequest).where(AccountLinkRequest.id == request_id)
        return (await self.session.scalars(stmt)).one_or_none()

    async def get_request_by_token(self, request_token: str) -> AccountLinkRequest | None:
        """Retrieve an account link request by its token."""
        stmt = select(AccountLinkRequest).where(AccountLinkRequest.request_token == request_token)
        return (await self.session.scalars(stmt)).one_or_none()

    async def get_requests_by_user_identity_id(self, user_identity_id: int) -> Sequence[AccountLinkRequest]:
        """Retrieve all requests for a specific user identity."""
        stmt = select(AccountLinkRequest).where(AccountLinkRequest.user_identity_id == user_identity_id)
        return (await self.session.scalars(stmt)).all()

    async def get_pending_requests_by_user_identity_id(self, user_identity_id: int) -> Sequence[AccountLinkRequest]:
        """Retrieve all pending requests for a specific user identity."""
        stmt = select(AccountLinkRequest).where(
            AccountLinkRequest.user_identity_id == user_identity_id,
            AccountLinkRequest.status == "pending",
        )
        return (await self.session.scalars(stmt)).all()

    async def get_expired_requests(self) -> Sequence[AccountLinkRequest]:
        """Retrieve all expired requests."""
        now = datetime.now(UTC)
        stmt = select(AccountLinkRequest).where(
            AccountLinkRequest.expires_at < now,
            AccountLinkRequest.status == "pending",
        )
        return (await self.session.scalars(stmt)).all()

    async def create_request(self, request: AccountLinkRequest) -> AccountLinkRequest:
        """Create a new account link request and persist it to the database."""
        self.session.add(request)
        await self.session.flush()
        return request

    async def update_request(self, request: AccountLinkRequest) -> AccountLinkRequest:
        """Update an existing account link request and commit changes to the database."""
        await self.session.flush()
        return request

    async def delete_request(self, id: int) -> None:
        """Delete an account link request by its ID if it exists."""
        stmt = delete(AccountLinkRequest).where(AccountLinkRequest.id == id)
        await self.session.execute(stmt)
        await self.session.flush()
