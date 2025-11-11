"""
Member management service.
"""

import app.db as database
from app.core.i18n import _


def add_new_member(email: str, name: str) -> str:
    """
    Adds a new member to the group.
    - If member exists (active or inactive): returns error (use rejoin_member for inactive members).
    - If member doesn't exist: adds new member.
    """
    existing_member = database.get_member_by_email(email)
    if existing_member:
        if existing_member.is_active is True:
            return _(
                "Error: Member with email '{}' already exists and is active."
            ).format(email)
        else:
            return _(
                "Error: Member with email '{}' exists but is inactive. Please use rejoin option."
            ).format(email)

    # Add the new member
    new_member_id = database.add_member(email, name)
    if (
        new_member_id is None
    ):  # Should not happen if check for existing_member passed
        return _("Error: Could not add member '{}'.").format(name)

    return _("Member '{}' added successfully.").format(name)


def remove_member_by_id(member_id: int) -> str:
    """
    Removes (deactivates) a member from the group by ID.
    Returns a message describing what happened.
    """
    member = database.get_member_by_id(member_id)
    if not member:
        return _("Error: Member with ID {} not found.").format(member_id)

    if not member.is_active:
        return _("Error: Member '{}' is already inactive.").format(member.name)

    database.deactivate_member(member_id)
    return _("Member '{}' has been removed (deactivated).").format(member.name)


def rejoin_member_by_id(member_id: int) -> str:
    """
    Rejoins (reactivates) an inactive member by ID.
    Returns a message describing what happened.
    """
    member = database.get_member_by_id(member_id)
    if not member:
        return _("Error: Member with ID {} not found.").format(member_id)

    if member.is_active:
        return _("Error: Member '{}' is already active.").format(member.name)

    database.reactivate_member(member_id)
    return _("Member '{}' has been reactivated (rejoined).").format(
        member.name
    )


def update_member_by_id(member_id: int, is_active: bool | None = None) -> str:
    """
    Updates a member by ID.
    Currently supports updating is_active status.
    Returns a message describing what happened.
    """
    member = database.get_member_by_id(member_id)
    if not member:
        return _("Error: Member with ID {} not found.").format(member_id)

    if is_active is not None:
        if member.is_active == is_active:
            status_text = _("active") if is_active else _("inactive")
            return _("Error: Member '{}' is already {}.").format(
                member.name, status_text
            )

        if is_active:
            database.reactivate_member(member_id)
            return _("Member '{}' has been reactivated.").format(member.name)
        else:
            database.deactivate_member(member_id)
            return _("Member '{}' has been deactivated.").format(member.name)

    return _("Error: No fields to update.")


# Legacy functions for backward compatibility (used by CLI)
def remove_member(name: str) -> str:
    """
    Removes (deactivates) a member from the group by name.
    Returns a message describing what happened.
    Note: This is a legacy function. Use remove_member_by_id for API.
    """
    member = database.get_member_by_name(name)
    if not member:
        return _("Error: Member '{}' not found.").format(name)

    if not member.is_active:
        return _("Error: Member '{}' is already inactive.").format(name)

    database.deactivate_member(member.id)
    return _("Member '{}' has been removed (deactivated).").format(name)


def rejoin_member(name: str) -> str:
    """
    Rejoins (reactivates) an inactive member by name.
    Returns a message describing what happened.
    Note: This is a legacy function. Use rejoin_member_by_id for API.
    """
    member = database.get_member_by_name(name)
    if not member:
        return _("Error: Member '{}' not found.").format(name)

    if member.is_active:
        return _("Error: Member '{}' is already active.").format(name)

    database.reactivate_member(member.id)
    return _("Member '{}' has been reactivated (rejoined).").format(name)
