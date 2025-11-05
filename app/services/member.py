"""
Member management service.
"""
import app.db as database
from app.core.i18n import _


def add_new_member(name: str) -> str:
    """
    Adds a new member to the group.
    - If member exists (active or inactive): returns error (use rejoin_member for inactive members).
    - If member doesn't exist: adds new member.
    """
    existing_member = database.get_member_by_name(name)
    if existing_member:
        if existing_member["is_active"]:
            return _("Error: Member '{}' already exists and is active.").format(name)
        else:
            return _("Error: Member '{}' exists but is inactive. Please use rejoin option.").format(name)

    # Add the new member
    new_member_id = database.add_member(name)
    if new_member_id is None:  # Should not happen if check for existing_member passed
        return _("Error: Could not add member '{}'.").format(name)

    return _("Member '{}' added successfully.").format(name)


def remove_member(name: str) -> str:
    """
    Removes (deactivates) a member from the group.
    Returns a message describing what happened.
    """
    member = database.get_member_by_name(name)
    if not member:
        return _("Error: Member '{}' not found.").format(name)

    if not member["is_active"]:
        return _("Error: Member '{}' is already inactive.").format(name)

    database.deactivate_member(member["id"])
    return _("Member '{}' has been removed (deactivated).").format(name)


def rejoin_member(name: str) -> str:
    """
    Rejoins (reactivates) an inactive member.
    Returns a message describing what happened.
    """
    member = database.get_member_by_name(name)
    if not member:
        return _("Error: Member '{}' not found.").format(name)

    if member["is_active"]:
        return _("Error: Member '{}' is already active.").format(name)

    database.reactivate_member(member["id"])
    return _("Member '{}' has been reactivated (rejoined).").format(name)

