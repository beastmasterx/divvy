"""
Transaction management service (expenses, deposits, refunds).
"""

import app.db as database
from app.core.i18n import _
from app.services.utils import cents_to_dollars, dollars_to_cents


def record_expense(
    description: str | None,
    amount_str: str,
    payer_name: str,
    category_name: str,
    is_personal: bool = False,
) -> str:
    """
    Records a new expense.
    - Converts amount to cents.
    - Validates participants.
    - Calculates the split and remainder.
    - Records the expense transaction in the database.
    - Updates the remainder-paid cycle for the member who paid the remainder.
    """
    try:
        amount_cents = dollars_to_cents(amount_str)
    except ValueError as e:
        return f"Error: {e}"

    payer = database.get_member_by_name(payer_name)
    if not payer:
        return _("Error: Payer '{}' not found.").format(payer_name)
    payer_id_for_transaction = payer["id"]

    category = database.get_category_by_name(category_name)
    if not category:
        return _("Error: Category '{}' not found.").format(category_name)

    # For personal expenses, only the payer owes the amount (no split, no remainder logic)
    if is_personal:
        # Record the personal expense transaction
        database.add_transaction(
            transaction_type="expense",
            amount=amount_cents,
            description=description,
            payer_id=payer_id_for_transaction,
            category_id=category["id"],
            is_personal=True,
        )

        if description:
            return _("Personal expense '{}' of {} recorded successfully.").format(
                description,
                cents_to_dollars(amount_cents),
            )
        else:
            return _("Personal expense of {} recorded successfully.").format(
                cents_to_dollars(amount_cents),
            )

    # For shared/individual expenses, split among active members
    active_members = database.get_active_members()
    if not active_members:
        return _("Error: No active members to split the expense among.")

    num_active_members = len(active_members)
    remainder = amount_cents % num_active_members

    remainder_payer_name = _("N/A")
    remainder_payer_id = None

    if remainder > 0:  # Only assign remainder if there is one
        # First, check if all members have paid a remainder in the current cycle
        all_paid_remainder = True
        for member in active_members:
            if not member["paid_remainder_in_cycle"]:
                all_paid_remainder = False
                break

        if all_paid_remainder:
            database.reset_all_member_remainder_status()
            # Re-fetch active members after reset to get updated status
            active_members = database.get_active_members()

        # Find the next member to pay the remainder
        for member in active_members:
            if not member["paid_remainder_in_cycle"]:
                remainder_payer_id = member["id"]
                remainder_payer_name = member["name"]
                database.update_member_remainder_status(member["id"], True)
                break

        if (
            remainder_payer_id is None
        ):  # Should not happen if logic is correct and active_members is not empty
            return _("Internal Error: Could not determine remainder payer.")

    # Record the expense transaction (not personal)
    database.add_transaction(
        transaction_type="expense",
        amount=amount_cents,
        description=description,
        payer_id=payer_id_for_transaction,
        category_id=category["id"],
        is_personal=False,
    )

    if description:
        return _(
            "Expense '{}' of {} recorded successfully. " "Remainder of {} assigned to {}."
        ).format(
            description,
            cents_to_dollars(amount_cents),
            cents_to_dollars(remainder),
            remainder_payer_name,
        )
    else:
        return _("Expense of {} recorded successfully. " "Remainder of {} assigned to {}.").format(
            cents_to_dollars(amount_cents),
            cents_to_dollars(remainder),
            remainder_payer_name,
        )


def record_deposit(
    description: str | None,
    amount_str: str,
    payer_name: str,
) -> str:
    """
    Records a new deposit from a member.
    - Converts amount to cents.
    - Validates the payer.
    - Records the deposit transaction in the database.
    """
    try:
        amount_cents = dollars_to_cents(amount_str)
    except ValueError as e:
        return f"Error: {e}"

    payer = database.get_member_by_name(payer_name)
    if not payer:
        return _("Error: Payer '{}' not found.").format(payer_name)

    # Record the deposit transaction
    database.add_transaction(
        transaction_type="deposit",
        amount=amount_cents,
        description=description,
        payer_id=payer["id"],
        category_id=None,
    )

    if description:
        return _("Deposit '{}' of {} from {} recorded successfully.").format(
            description,
            cents_to_dollars(amount_cents),
            payer_name,
        )
    else:
        return _("Deposit of {} from {} recorded successfully.").format(
            cents_to_dollars(amount_cents),
            payer_name,
        )


def record_refund(
    description: str | None,
    amount_str: str,
    recipient_name: str,
) -> str:
    """
    Records a refund to a member (active or inactive).
    - Converts amount to cents.
    - Validates the recipient.
    - Records the refund as a negative deposit transaction.
    """
    try:
        amount_cents = dollars_to_cents(amount_str)
    except ValueError as e:
        return f"Error: {e}"

    recipient = database.get_member_by_name(recipient_name)
    if not recipient:
        return _("Error: Member '{}' not found.").format(recipient_name)

    # Record refund as negative deposit (reduces recipient's balance)
    # Note: We store as positive amount, but mark it as refund in description
    refund_base = _("Refund to {}").format(recipient_name)
    refund_desc = description if description else refund_base
    if not description or not description.startswith(_("Refund")):
        refund_desc = _("Refund: {}").format(refund_desc) if description else refund_base

    database.add_transaction(
        transaction_type="deposit",
        amount=-amount_cents,  # Negative amount for refund
        description=refund_desc,
        payer_id=recipient["id"],  # Recipient gets the refund
        category_id=None,
    )

    # Use original description for display, not refund_desc (which always has a value)
    if description:
        return _("Refund '{}' of {} to {} recorded successfully.").format(
            description,
            cents_to_dollars(amount_cents),
            recipient_name,
        )
    else:
        return _("Refund of {} to {} recorded successfully.").format(
            cents_to_dollars(amount_cents),
            recipient_name,
        )
