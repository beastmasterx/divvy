#!/usr/bin/env python3
"""
ONE-TIME MIGRATION SCRIPT - DEPRECATED/ARCHIVED

This script was used to migrate data from SQLite to MySQL during the initial
database refactoring. It is kept for historical reference and documentation purposes.

⚠️  WARNING: This is a one-time migration script. Do not run it again unless
you understand the implications. Running it multiple times may create duplicate data.

Original purpose: Migrate data from SQLite database to MySQL (or other RDBMS).

Usage:
    python scripts/migrate_sqlite_to_mysql.py
    # or
    cd scripts && python migrate_sqlite_to_mysql.py
"""
import logging
import os
import sys
from pathlib import Path

# Add src to path (go up one level from scripts/ to project root)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import load_env_files
from divvy.database.models import Base, Member, Period, Category, Transaction
from divvy.database.connection import get_database_url, ensure_database_exists

# Set default log level to INFO for migration script (unless already set)
if "LOG_LEVEL" not in os.environ:
    os.environ["LOG_LEVEL"] = "INFO"

# Load .env files (both base .env and environment-specific .env.{ENV})
load_env_files(project_root)

# Setup logger for this script
logger = logging.getLogger(__name__)

# Source SQLite database path
# Try multiple possible locations
possible_paths = [
    project_root / "database" / "Expense.db",
    project_root / "data" / "expenses.db",
    project_root / "data" / "Expense.db",
]

SQLITE_DB_PATH = None
for path in possible_paths:
    if path.exists():
        SQLITE_DB_PATH = path
        break

# Check if SQLite database exists
if not SQLITE_DB_PATH or not SQLITE_DB_PATH.exists():
    logger.error(f"Error: SQLite database not found. Tried: {possible_paths}")
    sys.exit(1)

logger.info(f"Source SQLite database: {SQLITE_DB_PATH}")
logger.info(f"Target MySQL database: {get_database_url()}")

# Create SQLite engine (source)
sqlite_url = f"sqlite:///{SQLITE_DB_PATH}"
sqlite_engine = create_engine(sqlite_url, echo=False)

# Get MySQL connection URL (target)
mysql_url = get_database_url()

# Ensure MySQL database exists
logger.info("\nEnsuring MySQL database exists...")
ensure_database_exists(mysql_url)

# Create MySQL engine (target)
mysql_engine = create_engine(mysql_url, echo=False)

# Create sessions
SqliteSession = sessionmaker(bind=sqlite_engine)
MysqlSession = sessionmaker(bind=mysql_engine)

logger.info("\nCreating tables in MySQL database...")
# Create all tables in MySQL
Base.metadata.create_all(bind=mysql_engine)

sqlite_session = SqliteSession()
mysql_session = MysqlSession()

try:
    # Migrate Categories first (no dependencies)
    logger.info("\nMigrating categories...")
    sqlite_categories = sqlite_session.query(Category).all()
    category_id_map = {}  # Map old ID to new ID
    for cat in sqlite_categories:
        # Check if category already exists in MySQL
        existing = mysql_session.query(Category).filter_by(name=cat.name).first()
        if existing:
            category_id_map[cat.id] = existing.id
            logger.info(f"  Category '{cat.name}' already exists (ID: {existing.id})")
        else:
            new_cat = Category(name=cat.name)
            mysql_session.add(new_cat)
            mysql_session.flush()  # Get the new ID
            category_id_map[cat.id] = new_cat.id
            logger.info(f"  Migrated category '{cat.name}' (ID: {cat.id} -> {new_cat.id})")
    mysql_session.commit()

    # Migrate Members
    logger.info("\nMigrating members...")
    sqlite_members = sqlite_session.query(Member).all()
    member_id_map = {}  # Map old ID to new ID
    for member in sqlite_members:
        # Check if member already exists in MySQL
        existing = mysql_session.query(Member).filter_by(name=member.name).first()
        if existing:
            member_id_map[member.id] = existing.id
            logger.info(f"  Member '{member.name}' already exists (ID: {existing.id})")
        else:
            new_member = Member(
                name=member.name,
                is_active=bool(member.is_active),
                paid_remainder_in_cycle=bool(member.paid_remainder_in_cycle)
            )
            mysql_session.add(new_member)
            mysql_session.flush()  # Get the new ID
            member_id_map[member.id] = new_member.id
            logger.info(f"  Migrated member '{member.name}' (ID: {member.id} -> {new_member.id})")
    mysql_session.commit()

    # Migrate Periods
    logger.info("\nMigrating periods...")
    sqlite_periods = sqlite_session.query(Period).all()
    period_id_map = {}  # Map old ID to new ID
    for period in sqlite_periods:
        # Check if period already exists (by name and start_date)
        existing = mysql_session.query(Period).filter_by(
            name=period.name,
            start_date=period.start_date
        ).first()
        if existing:
            period_id_map[period.id] = existing.id
            logger.info(f"  Period '{period.name}' already exists (ID: {existing.id})")
        else:
            new_period = Period(
                name=period.name,
                start_date=period.start_date,
                end_date=period.end_date,
                is_settled=bool(period.is_settled),
                settled_date=period.settled_date
            )
            mysql_session.add(new_period)
            mysql_session.flush()  # Get the new ID
            period_id_map[period.id] = new_period.id
            logger.info(f"  Migrated period '{period.name}' (ID: {period.id} -> {new_period.id})")
    mysql_session.commit()

    # Migrate Transactions (last, as it has foreign keys)
    logger.info("\nMigrating transactions...")
    sqlite_transactions = sqlite_session.query(Transaction).all()
    migrated_count = 0
    skipped_count = 0
    for tx in sqlite_transactions:
        # Map foreign key IDs
        new_payer_id = member_id_map.get(tx.payer_id) if tx.payer_id else None
        new_category_id = category_id_map.get(tx.category_id) if tx.category_id else None
        new_period_id = period_id_map.get(tx.period_id) if tx.period_id else None

        # Check if all foreign keys are valid
        if tx.period_id and new_period_id is None:
            logger.warning(f"  Warning: Transaction {tx.id} has invalid period_id {tx.period_id}, skipping")
            skipped_count += 1
            continue

        # Check if transaction already exists (by key attributes)
        existing = mysql_session.query(Transaction).filter_by(
            transaction_type=tx.transaction_type,
            amount=tx.amount,
            payer_id=new_payer_id,
            period_id=new_period_id,
            timestamp=tx.timestamp
        ).first()
        
        if existing:
            logger.info(f"  Transaction {tx.id} already exists (ID: {existing.id})")
            skipped_count += 1
            continue

        new_tx = Transaction(
            transaction_type=tx.transaction_type,
            description=tx.description,
            amount=tx.amount,
            payer_id=new_payer_id,
            category_id=new_category_id,
            period_id=new_period_id,
            is_personal=bool(tx.is_personal),
            timestamp=tx.timestamp
        )
        mysql_session.add(new_tx)
        migrated_count += 1
        if migrated_count % 50 == 0:
            logger.info(f"  Migrated {migrated_count} transactions...")
    
    mysql_session.commit()
    logger.info(f"\n✓ Migration completed!")
    logger.info(f"  Categories: {len(sqlite_categories)}")
    logger.info(f"  Members: {len(sqlite_members)}")
    logger.info(f"  Periods: {len(sqlite_periods)}")
    logger.info(f"  Transactions: {migrated_count} migrated, {skipped_count} skipped")

except Exception as e:
    mysql_session.rollback()
    logger.error(f"\n✗ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    sqlite_session.close()
    mysql_session.close()
    sqlite_engine.dispose()
    mysql_engine.dispose()

logger.info("\nMigration script completed successfully!")

