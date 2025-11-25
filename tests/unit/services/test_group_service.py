"""
Unit tests for GroupService.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.schemas import GroupRequest
from app.services import GroupService, UserService
from tests.fixtures.factories import create_test_group, create_test_user


@pytest.mark.unit
class TestGroupService:
    """Test suite for GroupService."""

    async def test_get_all_groups(self, db_session: AsyncSession):
        """Test retrieving all groups."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        # Create some groups
        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group1 = create_test_group(name="Group 1", owner_id=user.id)
        group2 = create_test_group(name="Group 2", owner_id=user.id)
        db_session.add(group1)
        db_session.add(group2)
        await db_session.commit()

        groups = await service.get_all_groups()
        assert len(groups) >= 2

        group_names = {g.name for g in groups}
        assert "Group 1" in group_names
        assert "Group 2" in group_names

    async def test_get_group_by_id_exists(self, db_session: AsyncSession):
        """Test retrieving a group by ID when it exists."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        retrieved = await service.get_group_by_id(group.id)
        assert retrieved is not None
        assert retrieved.id == group.id
        assert retrieved.name == "Test Group"

    async def test_get_group_by_id_not_exists(self, db_session: AsyncSession):
        """Test retrieving a group by ID when it doesn't exist."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        result = await service.get_group_by_id(99999)
        assert result is None

    async def test_create_group(self, db_session: AsyncSession):
        """Test creating a new group."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        request = GroupRequest(name="New Group")
        created = await service.create_group(request, owner_id=user.id)

        assert created.id is not None
        assert created.name == "New Group"
        assert created.owner_id == user.id

        # Verify it's in the database
        retrieved = await service.get_group_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == "New Group"
        assert retrieved.owner_id == user.id

    async def test_update_group_exists(self, db_session: AsyncSession):
        """Test updating an existing group."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Original Name", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        request = GroupRequest(name="Updated Name")
        updated = await service.update_group(group.id, request)

        assert updated.name == "Updated Name"

        # Verify the update persisted
        retrieved = await service.get_group_by_id(group.id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"

    async def test_update_group_not_exists(self, db_session: AsyncSession):
        """Test updating a non-existent group raises NotFoundError."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        request = GroupRequest(name="Updated Name")

        with pytest.raises(NotFoundError):
            await service.update_group(99999, request)

    async def test_get_users_by_group_id(self, db_session: AsyncSession):
        """Test retrieving users for a group."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()

        users = await service.get_users_by_group_id(group.id)
        assert isinstance(users, list)
        # Group should have no users initially (except owner via relationship)

    async def test_add_user_to_group(self, db_session: AsyncSession):
        """Test adding a user to a group."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        owner = create_test_user(email="owner@example.com", name="Owner")
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(owner)
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=owner.id)
        db_session.add(group)
        await db_session.commit()

        # Add user to group
        await service.add_user_to_group(group.id, user.id)

        # Verify user is in group
        users = await service.get_users_by_group_id(group.id)
        user_ids = {u.id for u in users}
        assert user.id in user_ids

    async def test_add_user_to_group_already_member(self, db_session: AsyncSession):
        """Test adding a user who is already in the group raises ConflictError."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        owner = create_test_user(email="owner@example.com", name="Owner")
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(owner)
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=owner.id)
        db_session.add(group)
        await db_session.commit()

        # Add user to group first time
        await service.add_user_to_group(group.id, user.id)

        # Try to add again - should raise ConflictError
        with pytest.raises(ConflictError):
            await service.add_user_to_group(group.id, user.id)

    async def test_add_user_to_group_not_exists(self, db_session: AsyncSession):
        """Test adding user to non-existent group raises NotFoundError."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        user = create_test_user(email="user@example.com", name="User")
        db_session.add(user)
        await db_session.commit()

        with pytest.raises(NotFoundError):
            await service.add_user_to_group(99999, user.id)

    async def test_remove_user_from_group(self, db_session: AsyncSession):
        """Test removing a user from a group."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        owner = create_test_user(email="owner@example.com", name="Owner")
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(owner)
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=owner.id)
        db_session.add(group)
        await db_session.commit()

        # Add user to group first
        await service.add_user_to_group(group.id, user.id)

        # Remove user from group
        await service.remove_user_from_group(group.id, user.id)

        # Verify user is not in group
        users = await service.get_users_by_group_id(group.id)
        user_ids = {u.id for u in users}
        assert user.id not in user_ids

    async def test_remove_user_from_group_not_member(self, db_session: AsyncSession):
        """Test removing a user who is not in the group raises NotFoundError."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        owner = create_test_user(email="owner@example.com", name="Owner")
        user = create_test_user(email="user@example.com", name="User")
        db_session.add(owner)
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="Test Group", owner_id=owner.id)
        db_session.add(group)
        await db_session.commit()

        with pytest.raises(NotFoundError):
            await service.remove_user_from_group(group.id, user.id)

    async def test_delete_group_exists(self, db_session: AsyncSession):
        """Test deleting a group."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        user = create_test_user(email="owner@example.com", name="Owner")
        db_session.add(user)
        await db_session.commit()

        group = create_test_group(name="To Delete", owner_id=user.id)
        db_session.add(group)
        await db_session.commit()
        group_id = group.id

        # Should succeed if no active period with transactions
        await service.delete_group(group_id)

        # Verify group is deleted
        retrieved = await service.get_group_by_id(group_id)
        assert retrieved is None

    async def test_delete_group_not_exists(self, db_session: AsyncSession):
        """Test deleting a non-existent group raises NotFoundError."""
        user_service = UserService(db_session)
        service = GroupService(db_session, user_service)

        with pytest.raises(NotFoundError):
            await service.delete_group(99999)
