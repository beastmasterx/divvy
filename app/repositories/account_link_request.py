"""
Repository for managing account link request entities.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountLinkRequest


class AccountLinkRequestRepository:
    """Repository for managing account link request entities."""

    def __init__(self, session: Session):
        self.session = session

    def get_request_by_id(self, request_id: int) -> AccountLinkRequest | None:
        """Retrieve a specific account link request by its ID."""
        stmt = select(AccountLinkRequest).where(AccountLinkRequest.id == request_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_request_by_token(self, request_token: str) -> AccountLinkRequest | None:
        """Retrieve an account link request by its token."""
        stmt = select(AccountLinkRequest).where(AccountLinkRequest.request_token == request_token)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_requests_by_user_identity_id(self, user_identity_id: int) -> Sequence[AccountLinkRequest]:
        """Retrieve all requests for a specific user identity."""
        stmt = select(AccountLinkRequest).where(AccountLinkRequest.user_identity_id == user_identity_id)
        return self.session.execute(stmt).scalars().all()

    def get_pending_requests_by_user_identity_id(
        self, user_identity_id: int
    ) -> Sequence[AccountLinkRequest]:
        """Retrieve all pending requests for a specific user identity."""
        stmt = select(AccountLinkRequest).where(
            AccountLinkRequest.user_identity_id == user_identity_id,
            AccountLinkRequest.status == "pending",
        )
        return self.session.execute(stmt).scalars().all()

    def get_expired_requests(self) -> Sequence[AccountLinkRequest]:
        """Retrieve all expired requests."""
        now = datetime.now(UTC)
        stmt = select(AccountLinkRequest).where(
            AccountLinkRequest.expires_at < now,
            AccountLinkRequest.status == "pending",
        )
        return self.session.execute(stmt).scalars().all()

    def create_request(self, request: AccountLinkRequest) -> AccountLinkRequest:
        """Create a new account link request and persist it to the database."""
        self.session.add(request)
        self.session.commit()
        return request

    def update_request(self, request: AccountLinkRequest) -> AccountLinkRequest:
        """Update an existing account link request and commit changes to the database."""
        self.session.commit()
        return request

    def delete_request(self, request_id: int) -> None:
        """Delete an account link request by its ID if it exists."""
        request = self.get_request_by_id(request_id)
        if request:
            self.session.delete(request)
            self.session.commit()

