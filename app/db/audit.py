"""
SQLAlchemy event listeners for automatic audit field management.
"""

from contextvars import ContextVar
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models.models import AuditMixin

# Context variable to store current user ID per request
_current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def set_current_user_id(user_id: int | None) -> None:
    """
    Set the current user ID in the request context.

    Args:
        user_id: The ID of the current authenticated user, or None
    """
    _current_user_id.set(user_id)


def get_current_user_id() -> int | None:
    """
    Get the current user ID from the request context.

    Returns:
        The current user ID, or None if not set
    """
    return _current_user_id.get()


def clear_current_user_id() -> None:
    """Clear the current user ID from context (useful for cleanup)."""
    _current_user_id.set(None)


@event.listens_for(Session, "before_flush")
def receive_before_flush(session: Session, flush_context: Any, instances: Any) -> None:
    """
    SQLAlchemy event listener that automatically sets audit fields.

    This listener runs before SQLAlchemy flushes changes to the database.

    Args:
        session: The SQLAlchemy session
        flush_context: The flush context (unused, but required by SQLAlchemy event API)
        instances: Instances being flushed (unused, we iterate session instead)
    """
    current_user_id = get_current_user_id()

    # Skip if no user context (e.g., system operations, migrations)
    # This allows operations without audit tracking when needed
    if current_user_id is None:
        return

    # Process new entities (INSERT operations)
    for instance in session.new:
        if isinstance(instance, AuditMixin) and instance.created_by is None:
            # Only set if not already set (allows manual override)
            instance.created_by = current_user_id
            # created_at is already handled by TimestampMixin default

    # Process modified entities (UPDATE operations)
    for instance in session.dirty:
        if isinstance(instance, AuditMixin):
            # Always update updated_by on modification
            instance.updated_by = current_user_id
            # updated_at is already handled by TimestampMixin onupdate

    # Process deleted entities (DELETE operations)
    for instance in session.deleted:
        if isinstance(instance, AuditMixin):
            pass
