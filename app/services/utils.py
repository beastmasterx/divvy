"""
Utility functions for services.
"""

from app.core.i18n import _
from app.exceptions import ValidationError


def cents_to_dollars(cents: int) -> str:
    """Converts an amount in cents to a dollar string (e.g., 12345 -> "123.45")."""
    return f"{cents / 100:.2f}"


def dollars_to_cents(dollars_str: str) -> int:
    """Converts a dollar string to an amount in cents (e.g., "123.45" -> 12345)."""
    try:
        return int(float(dollars_str) * 100)
    except ValueError as err:
        raise ValidationError(_("Invalid amount format. Please enter a number.")) from err
