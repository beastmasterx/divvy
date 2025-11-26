#!/usr/bin/env python3
"""
Script to initialize the system admin user.

Usage:
    python scripts/init_admin.py
    python scripts/init_admin.py --email admin@example.com --password secret123 --name "Admin User"
    python scripts/init_admin.py --email admin@example.com
"""

import argparse
import asyncio
import secrets
import string
import sys
from pathlib import Path

from app.core.config import load_env_files
from app.core.security.password import hash_password
from app.db.session import get_session
from app.exceptions import ConflictError
from app.models import SystemRole
from app.repositories import AuthorizationRepository, UserRepository
from app.services import AuthorizationService, UserService

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_random_password(length: int = 16) -> str:
    """
    Generate a strong random password.

    Args:
        length: Length of the password (default: 16)

    Returns:
        Random password string containing uppercase, lowercase, digits, and special characters
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def init_admin(
    email: str,
    password: str,
    name: str,
) -> None:
    """
    Initialize the system admin user.

    Args:
        email: Admin user email
        password: Admin user password (will be hashed)
        name: Admin user name

    Raises:
        ConflictError: If user with email already exists
    """
    async with get_session() as session:
        user_repository = UserRepository(session)
        auth_repository = AuthorizationRepository(session)
        user_service = UserService(session)
        auth_service = AuthorizationService(session)

        # Check if user already exists
        existing_user = await user_repository.get_user_by_email(email)
        if existing_user:
            # Check if user already has admin role
            system_role = await auth_repository.get_system_role(existing_user.id)
            if system_role == SystemRole.ADMIN.value:
                print(f"✓ Admin user already exists: {email}")
                print(f"  User ID: {existing_user.id}")
                print(f"  Name: {existing_user.name}")
                return

            # User exists but doesn't have admin role - assign it
            print(f"⚠ User exists but doesn't have admin role: {email}")
            print("  Assigning system:admin role...")
            await auth_service.assign_system_role(existing_user.id, SystemRole.ADMIN)
            print("✓ Admin role assigned successfully!")
            return

        # Create new admin user
        print("Creating admin user...")
        print(f"  Email: {email}")
        print(f"  Name: {name}")

        # Hash password
        hashed_password = hash_password(password)

        # Create user
        from app.schemas import UserRequest

        user_request = UserRequest(
            email=email,
            name=name,
            password=hashed_password,
            is_active=True,
        )
        user = await user_service.create_user(user_request)

        # Assign system:admin role
        await auth_service.assign_system_role(user.id, SystemRole.ADMIN)

        print("✓ Admin user created successfully!")
        print(f"  User ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.name}")
        print("\n⚠ IMPORTANT: Save this password securely!")
        print(f"  Password: {password}")


def main() -> None:
    """Main entry point for the script."""
    # Load environment variables first (for database connection, etc.)
    load_env_files()

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Initialize the system admin user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/init_admin.py
  python scripts/init_admin.py --email admin@example.com --password secret123
  python scripts/init_admin.py --email admin@example.com --password secret123 --name "Admin User"
        """,
    )

    parser.add_argument(
        "--email",
        type=str,
        default="admin@divvy.local",
        help="Admin user email address (default: admin@divvy.local)",
    )

    # Generate random password by default
    default_password = generate_random_password()

    parser.add_argument(
        "--password",
        type=str,
        default=default_password,
        help="Admin user password (default: randomly generated 16-character string)",
    )

    parser.add_argument(
        "--name",
        type=str,
        default="System Administrator",
        help="Admin user name (default: System Administrator)",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.email:
        print("Error: Email cannot be empty")
        sys.exit(1)

    if not args.password:
        print("Error: Password cannot be empty")
        sys.exit(1)

    if not args.name:
        print("Error: Name cannot be empty")
        sys.exit(1)

    # Run async function
    try:
        asyncio.run(init_admin(args.email, args.password, args.name))
    except ConflictError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
