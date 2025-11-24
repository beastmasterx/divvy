"""
Unit tests for AccountLinkRequestRepository.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import AccountLinkRequestStatus
from app.repositories import AccountLinkRequestRepository
from tests.fixtures.factories import (
    create_test_account_link_request,
    create_test_user,
    create_test_user_identity,
)


@pytest.mark.unit
class TestAccountLinkRequestRepository:
    """Test suite for AccountLinkRequestRepository."""

    def test_get_request_by_id_exists(self, db_session: Session):
        """Test retrieving an account link request by ID when it exists."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create a request
        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="test_token_123",
        )
        db_session.add(request)
        db_session.commit()
        request_id = request.id

        retrieved = repo.get_request_by_id(request_id)
        assert retrieved is not None
        assert retrieved.id == request_id
        assert retrieved.request_token == "test_token_123"
        assert retrieved.user_identity_id == identity.id
        assert retrieved.status == AccountLinkRequestStatus.PENDING.value

    def test_get_request_by_id_not_exists(self, db_session: Session):
        """Test retrieving an account link request by ID when it doesn't exist."""
        repo = AccountLinkRequestRepository(db_session)
        result = repo.get_request_by_id(99999)
        assert result is None

    def test_get_request_by_token_exists(self, db_session: Session):
        """Test retrieving an account link request by token when it exists."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="google", external_id="go_456")
        db_session.add(identity)
        db_session.commit()

        # Create a request
        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="unique_token_789",
        )
        db_session.add(request)
        db_session.commit()

        retrieved = repo.get_request_by_token("unique_token_789")
        assert retrieved is not None
        assert retrieved.request_token == "unique_token_789"
        assert retrieved.user_identity_id == identity.id

    def test_get_request_by_token_not_exists(self, db_session: Session):
        """Test retrieving an account link request by token when it doesn't exist."""
        repo = AccountLinkRequestRepository(db_session)
        result = repo.get_request_by_token("nonexistent_token")
        assert result is None

    def test_get_requests_by_user_identity_id_empty(self, db_session: Session):
        """Test retrieving requests for a user identity when none exist."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        requests = repo.get_requests_by_user_identity_id(identity.id)
        assert isinstance(requests, list)
        assert len(requests) == 0

    def test_get_requests_by_user_identity_id_multiple(self, db_session: Session):
        """Test retrieving all requests for a user identity when multiple exist."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create multiple requests
        request1 = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="token_1",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        request2 = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="token_2",
            status=AccountLinkRequestStatus.APPROVED.value,
        )
        db_session.add(request1)
        db_session.add(request2)
        db_session.commit()

        requests = repo.get_requests_by_user_identity_id(identity.id)
        assert len(requests) == 2
        tokens = {req.request_token for req in requests}
        assert "token_1" in tokens
        assert "token_2" in tokens

    def test_get_pending_requests_by_user_identity_id(self, db_session: Session):
        """Test retrieving only pending requests for a user identity."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create requests with different statuses
        pending_request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="pending_token",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        approved_request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approved_token",
            status=AccountLinkRequestStatus.APPROVED.value,
        )
        expired_request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="expired_token",
            status=AccountLinkRequestStatus.EXPIRED.value,
        )
        db_session.add(pending_request)
        db_session.add(approved_request)
        db_session.add(expired_request)
        db_session.commit()

        pending_requests = repo.get_pending_requests_by_user_identity_id(identity.id)
        assert len(pending_requests) == 1
        assert pending_requests[0].request_token == "pending_token"
        assert pending_requests[0].status == AccountLinkRequestStatus.PENDING.value

    def test_get_expired_requests(self, db_session: Session):
        """Test retrieving all expired requests."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create requests with different expiration times
        expired_request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="expired_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired 1 hour ago
        )
        future_request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="future_token",
            status=AccountLinkRequestStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=24),  # Expires in 24 hours
        )
        # Approved request (should not be included even if expired)
        approved_expired = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="approved_expired_token",
            status=AccountLinkRequestStatus.APPROVED.value,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db_session.add(expired_request)
        db_session.add(future_request)
        db_session.add(approved_expired)
        db_session.commit()

        expired_requests = repo.get_expired_requests()
        assert len(expired_requests) == 1
        assert expired_requests[0].request_token == "expired_token"
        assert expired_requests[0].status == AccountLinkRequestStatus.PENDING.value

    def test_create_request(self, db_session: Session):
        """Test creating a new account link request."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create a request
        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="new_token_123",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        created = repo.create_request(request)

        assert created.id is not None
        assert created.request_token == "new_token_123"
        assert created.user_identity_id == identity.id
        assert created.status == AccountLinkRequestStatus.PENDING.value

        # Verify it's in the database
        retrieved = repo.get_request_by_id(created.id)
        assert retrieved is not None
        assert retrieved.request_token == "new_token_123"

    def test_update_request(self, db_session: Session):
        """Test updating an existing account link request."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create a request
        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="update_token",
            status=AccountLinkRequestStatus.PENDING.value,
        )
        db_session.add(request)
        db_session.commit()

        # Update it
        request.status = AccountLinkRequestStatus.APPROVED.value
        request.verified_at = datetime.now(UTC)
        updated = repo.update_request(request)

        assert updated.status == AccountLinkRequestStatus.APPROVED.value
        assert updated.verified_at is not None

        # Verify the update persisted
        retrieved = repo.get_request_by_id(request.id)
        assert retrieved is not None
        assert retrieved.status == AccountLinkRequestStatus.APPROVED.value
        assert retrieved.verified_at is not None

    def test_delete_request_exists(self, db_session: Session):
        """Test deleting an account link request that exists."""
        repo = AccountLinkRequestRepository(db_session)

        # Create a user and identity first
        user = create_test_user(email="test@example.com", name="Test User")
        db_session.add(user)
        db_session.commit()

        identity = create_test_user_identity(user_id=user.id, identity_provider="microsoft", external_id="ext_123")
        db_session.add(identity)
        db_session.commit()

        # Create a request
        request = create_test_account_link_request(
            user_identity_id=identity.id,
            request_token="delete_token",
        )
        db_session.add(request)
        db_session.commit()
        request_id = request.id

        # Delete it
        repo.delete_request(request_id)

        # Verify it's gone
        retrieved = repo.get_request_by_id(request_id)
        assert retrieved is None

    def test_delete_request_not_exists(self, db_session: Session):
        """Test deleting an account link request that doesn't exist (should not raise error)."""
        repo = AccountLinkRequestRepository(db_session)
        # Should not raise an exception
        repo.delete_request(99999)
