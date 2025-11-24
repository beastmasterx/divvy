"""
SQLAlchemy event listeners for automatic audit field management.
Supports async sessions only.
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


def _set_audit_fields(session: Session, current_user_id: int | None) -> None:
    """
    Helper function to set audit fields on the underlying synchronous session.

    Args:
        session: The underlying synchronous SQLAlchemy Session instance.
        current_user_id: The current user ID from context.
    """
    # Skip if no user context
    if current_user_id is None:
        return

    # Process new entities (INSERT operations)
    # session.new is a set of state objects, the instance is accessible via .instance
    for instance in session.new:
        # Check if the object being added inherits from AuditMixin and has no created_by set
        if isinstance(instance, AuditMixin) and getattr(instance, "created_by", None) is None:
            instance.created_by = current_user_id

    # Process modified entities (UPDATE operations)
    # session.dirty is a set of state objects
    for instance in session.dirty:
        # Check if the object being modified inherits from AuditMixin
        if isinstance(instance, AuditMixin):
            # Always set updated_by on modification
            instance.updated_by = current_user_id

    # session.deleted is a set of state objects. No audit field logic usually needed for DELETE.
    # for instance in session.deleted:
    #     if isinstance(instance, AuditMixin):
    #         pass


@event.listens_for(Session, "before_flush")
def receive_before_flush(session: Session, flush_context: Any, instances: Any) -> None:
    """
    SQLAlchemy event listener that automatically sets audit fields.

    This listener runs on the underlying synchronous Session, which is called
    by AsyncSession when an operation like commit/flush is awaited.
    """
    # NOTE: This function MUST be synchronous. No 'await' calls allowed here.

    # Assuming get_current_user_id() is a synchronous function that safely
    # retrieves the ID from a synchronous context (e.g., threading.local or contextvars).
    current_user_id = get_current_user_id()

    _set_audit_fields(session, current_user_id)
