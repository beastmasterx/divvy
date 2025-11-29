"""
Shared utility functions for authorization modules.
"""

from collections.abc import Sequence

from app.core.i18n import _
from app.models import GroupRole, SystemRole

# Type alias for the acceptable role types (Enum or str)
RoleType = SystemRole | GroupRole | str


def normalize_roles(roles: Sequence[RoleType]) -> list[str]:
    """
    Converts a sequence of Role Enums (SystemRole/GroupRole) or strings into
    a list of standardized role string values for authorization checks.

    Args:
        roles: Sequence of role enums or strings to normalize

    Returns:
        List of normalized role string values
    """
    normalized: list[str] = []
    for role in roles:
        # Use isinstance() for robust type checking against the Enum types
        if isinstance(role, (SystemRole, GroupRole)):
            # Enums must provide a .value attribute
            normalized.append(role.value)
        else:
            # Assume it's a string, or convert non-Enum/non-string to string
            normalized.append(str(role))
    return normalized


def get_display_role_name(role_value: str) -> str:
    """
    Returns the translated, display-friendly name for an internal role value.

    This prepares the string (e.g., "system:admin" -> "System Admin") and wraps
    it in the translation marker (`_()`) for i18n tooling.

    Args:
        role_value: The internal role value string

    Returns:
        Translated, display-friendly role name
    """
    # 1. Clean the role value: remove prefix (if exists) and replace underscores
    clean_name = role_value.split(":")[-1].replace("_", " ")

    # 2. Translate the title-cased, cleaned string
    # E.g., translates "System Admin"
    return _(clean_name.title())

