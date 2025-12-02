#!/usr/bin/env python3
"""
Script to seed the database with sample data for testing.

This script creates a realistic dataset including:
- Multiple users
- Groups with periods
- Various transactions (expenses, deposits, refunds)
- Expense shares
- Settlements

Sample Data:
    Users: 4 users (Alice, Bob, Charlie, Diana) with password "password123"
    Groups: 2 groups
        - "Apartment Roommates" (Alice, Bob, Charlie)
        - "Weekend Trip Group" (Bob, Charlie, Diana)
    Periods: 3 periods
        - "January 2024" (open, Apartment Roommates)
        - "December 2023" (closed, Apartment Roommates)
        - "Summer Trip 2024" (open, Weekend Trip Group)

Usage:
    python scripts/seed_sample_data.py
    python scripts/seed_sample_data.py --clear  # Clear existing data first
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path BEFORE importing app modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_env_files  # noqa: E402
from app.core.security.password import hash_password  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.models import (  # noqa: E402
    Category,
    ExpenseShare,
    Group,
    Period,
    PeriodStatus,
    Settlement,
    SplitKind,
    Transaction,
    TransactionKind,
    TransactionStatus,
    User,
)


async def clear_existing_data(session: AsyncSession) -> None:
    """Clear all existing data (except categories which are seeded by migrations)."""
    print("Clearing existing data...")

    # Delete in reverse order of dependencies
    await session.execute(delete(Settlement))
    await session.execute(delete(ExpenseShare))
    await session.execute(delete(Transaction))
    await session.execute(delete(Period))
    await session.execute(delete(Group))
    await session.execute(delete(User))

    await session.commit()
    print("✓ Existing data cleared")


async def get_or_create_categories(session: AsyncSession) -> dict[str, Category]:
    """Get existing categories or create default ones."""
    result = await session.execute(select(Category))
    existing_categories = {cat.name: cat for cat in result.scalars().all()}

    # Default categories (should exist from migrations, but create if missing)
    default_categories = [
        "Utilities (Water & Electricity & Gas)",
        "Groceries",
        "Daily Necessities",
        "Rent",
        "Other",
    ]

    categories: dict[str, Category] = {}
    for cat_name in default_categories:
        if cat_name in existing_categories:
            categories[cat_name] = existing_categories[cat_name]
        else:
            category = Category(name=cat_name, is_default=True)
            session.add(category)
            categories[cat_name] = category

    await session.flush()
    return categories


async def create_sample_users(session: AsyncSession) -> list[User]:
    """Create sample users."""
    print("\nCreating sample users...")

    users: list[User] = []
    user_configs = [
        ("Alice Johnson", "alice@example.com", "password123"),
        ("Bob Smith", "bob@example.com", "password123"),
        ("Charlie Brown", "charlie@example.com", "password123"),
        ("Diana Prince", "diana@example.com", "password123"),
    ]

    for name, email, password in user_configs:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"  ✓ User already exists: {email}")
            users.append(existing_user)
        else:
            hashed_password = hash_password(password)
            user = User(
                name=name,
                email=email,
                password=hashed_password,
                is_active=True,
            )
            session.add(user)
            users.append(user)
            print(f"  ✓ Created user: {name} ({email})")

    await session.flush()
    return users


async def create_sample_groups(session: AsyncSession, users: list[User]) -> list[Group]:
    """Create sample groups."""
    print("\nCreating sample groups...")

    group1 = Group(
        name="Apartment Roommates",
        created_by=users[0].id,
    )
    session.add(group1)

    group2 = Group(
        name="Weekend Trip Group",
        created_by=users[1].id,
    )
    session.add(group2)

    groups = [group1, group2]

    await session.flush()
    for group in groups:
        print(f"  ✓ Created group: {group.name}")

    return groups


async def create_sample_periods(session: AsyncSession, groups: list[Group], users: list[User]) -> list[Period]:
    """Create sample periods."""
    print("\nCreating sample periods...")

    now = datetime.now(UTC)

    period1 = Period(
        group_id=groups[0].id,
        name="January 2024",
        status=PeriodStatus.OPEN,
        start_date=now - timedelta(days=60),
        end_date=None,
        created_by=users[0].id,
    )
    session.add(period1)

    period2 = Period(
        group_id=groups[0].id,
        name="December 2023",
        status=PeriodStatus.CLOSED,
        start_date=now - timedelta(days=90),
        end_date=now - timedelta(days=60),
        closed_at=now - timedelta(days=60),
        created_by=users[0].id,
    )
    session.add(period2)

    period3 = Period(
        group_id=groups[1].id,
        name="Summer Trip 2024",
        status=PeriodStatus.OPEN,
        start_date=now - timedelta(days=30),
        end_date=None,
        created_by=users[1].id,
    )
    session.add(period3)

    periods = [period1, period2, period3]

    await session.flush()
    for period in periods:
        print(f"  ✓ Created period: {period.name} ({period.status.value})")

    return periods


async def create_sample_transactions(
    session: AsyncSession,
    periods: list[Period],
    users: list[User],
    categories: dict[str, Category],
) -> list[Transaction]:
    """Create sample transactions."""
    print("\nCreating sample transactions...")

    now = datetime.now(UTC)
    apartment_period = periods[0]
    trip_period = periods[2]
    closed_period = periods[1]

    # Define transaction data with their expense share users
    transaction_configs: list[dict[str, Any]] = [
        {
            "period": apartment_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.EQUAL,
            "amount": 12000,
            "description": "Monthly rent",
            "payer": users[0],
            "category": categories["Rent"],
            "date_incurred": now - timedelta(days=10),
            "status": TransactionStatus.APPROVED,
            "created_by": users[0].id,
            "share_users": [users[0], users[1], users[2]],
        },
        {
            "period": apartment_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.EQUAL,
            "amount": 8500,
            "description": "Utilities bill",
            "payer": users[1],
            "category": categories["Utilities (Water & Electricity & Gas)"],
            "date_incurred": now - timedelta(days=5),
            "status": TransactionStatus.APPROVED,
            "created_by": users[1].id,
            "share_users": [users[0], users[1], users[2]],
        },
        {
            "period": apartment_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.PERSONAL,
            "amount": 4500,
            "description": "Personal groceries",
            "payer": users[2],
            "category": categories["Groceries"],
            "date_incurred": now - timedelta(days=3),
            "status": TransactionStatus.APPROVED,
            "created_by": users[2].id,
            "share_users": [users[2]],
        },
        {
            "period": apartment_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.EQUAL,
            "amount": 3200,
            "description": "Shared groceries",
            "payer": users[0],
            "category": categories["Groceries"],
            "date_incurred": now - timedelta(days=2),
            "status": TransactionStatus.PENDING,
            "created_by": users[0].id,
            "share_users": [users[0], users[1], users[2]],
        },
        {
            "period": apartment_period,
            "transaction_kind": TransactionKind.DEPOSIT,
            "split_kind": SplitKind.PERSONAL,
            "amount": 5000,
            "description": "Security deposit refund",
            "payer": users[0],
            "category": categories["Other"],
            "date_incurred": now - timedelta(days=1),
            "status": TransactionStatus.APPROVED,
            "created_by": users[0].id,
            "share_users": [users[0]],
        },
        {
            "period": trip_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.EQUAL,
            "amount": 25000,
            "description": "Hotel booking",
            "payer": users[1],
            "category": categories["Other"],
            "date_incurred": now - timedelta(days=20),
            "status": TransactionStatus.APPROVED,
            "created_by": users[1].id,
            "share_users": [users[1], users[2], users[3]],
        },
        {
            "period": trip_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.EQUAL,
            "amount": 15000,
            "description": "Restaurant dinner",
            "payer": users[3],
            "category": categories["Other"],
            "date_incurred": now - timedelta(days=15),
            "status": TransactionStatus.APPROVED,
            "created_by": users[3].id,
            "share_users": [users[1], users[2], users[3]],
        },
        {
            "period": closed_period,
            "transaction_kind": TransactionKind.EXPENSE,
            "split_kind": SplitKind.EQUAL,
            "amount": 6000,
            "description": "December utilities",
            "payer": users[0],
            "category": categories["Utilities (Water & Electricity & Gas)"],
            "date_incurred": now - timedelta(days=70),
            "status": TransactionStatus.APPROVED,
            "created_by": users[0].id,
            "share_users": [users[0], users[1], users[2]],
        },
    ]

    # Create all transactions first
    transactions: list[Transaction] = []
    for config in transaction_configs:
        tx = Transaction(
            period_id=config["period"].id,
            transaction_kind=config["transaction_kind"],
            split_kind=config["split_kind"],
            amount=config["amount"],
            description=config["description"],
            payer_id=config["payer"].id,
            category_id=config["category"].id,
            date_incurred=config["date_incurred"],
            status=config["status"],
            created_by=config["created_by"],
        )
        session.add(tx)
        transactions.append(tx)

    # Flush to get transaction IDs
    await session.flush()

    # Now create expense shares with the transaction IDs
    for i, config in enumerate(transaction_configs):
        tx = transactions[i]
        for share_user in config["share_users"]:
            share = ExpenseShare(
                transaction_id=tx.id,
                user_id=share_user.id,
                created_by=config["created_by"],
            )
            session.add(share)

    await session.flush()
    for tx in transactions:
        print(f"  ✓ Created transaction: {tx.description} (${tx.amount/100:.2f})")

    return transactions


async def create_sample_settlements(
    session: AsyncSession, periods: list[Period], users: list[User]
) -> list[Settlement]:
    """Create sample settlements for the closed period."""
    print("\nCreating sample settlements...")

    # Only create settlements for closed periods
    closed_period = periods[1]  # December 2023

    settlement1 = Settlement(
        period_id=closed_period.id,
        payer_id=users[1].id,
        payee_id=users[0].id,
        amount=2000,  # $20.00
        date_paid=datetime.now(UTC) - timedelta(days=55),
        created_by=users[0].id,
    )
    session.add(settlement1)

    settlement2 = Settlement(
        period_id=closed_period.id,
        payer_id=users[2].id,
        payee_id=users[0].id,
        amount=2000,  # $20.00
        date_paid=datetime.now(UTC) - timedelta(days=55),
        created_by=users[0].id,
    )
    session.add(settlement2)

    settlements = [settlement1, settlement2]

    await session.flush()
    for settlement in settlements:
        payer = next(u for u in users if u.id == settlement.payer_id)
        payee = next(u for u in users if u.id == settlement.payee_id)
        print(f"  ✓ Created settlement: {payer.name} -> {payee.name} (${settlement.amount/100:.2f})")

    return settlements


async def seed_sample_data(clear_first: bool = False) -> None:
    """Seed the database with sample data."""
    async with get_session() as session:
        if clear_first:
            await clear_existing_data(session)

        print("=" * 60)
        print("Seeding sample data for testing")
        print("=" * 60)

        # Get or create categories
        categories = await get_or_create_categories(session)
        print(f"\n✓ Using {len(categories)} categories")

        # Create users
        users = await create_sample_users(session)

        # Create groups
        groups = await create_sample_groups(session, users)

        # Create periods
        periods = await create_sample_periods(session, groups, users)

        # Create transactions
        transactions = await create_sample_transactions(session, periods, users, categories)

        # Create settlements
        settlements = await create_sample_settlements(session, periods, users)

        print("\n" + "=" * 60)
        print("Sample data seeding completed!")
        print("=" * 60)
        print("\nSummary:")
        print(f"  Users: {len(users)}")
        print(f"  Groups: {len(groups)}")
        print(f"  Periods: {len(periods)}")
        print(f"  Transactions: {len(transactions)}")
        print(f"  Settlements: {len(settlements)}")
        print("\nTest user credentials:")
        print("  Email: alice@example.com, Password: password123")
        print("  Email: bob@example.com, Password: password123")
        print("  Email: charlie@example.com, Password: password123")
        print("  Email: diana@example.com, Password: password123")


def main() -> None:
    """Main entry point for the script."""
    # Load environment variables first (for database connection, etc.)
    load_env_files()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Seed the database with sample data for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/seed_sample_data.py
  python scripts/seed_sample_data.py --clear  # Clear existing data first
        """,
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing data before seeding (except categories)",
    )

    args = parser.parse_args()

    # Run async function
    try:
        asyncio.run(seed_sample_data(clear_first=args.clear))
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
