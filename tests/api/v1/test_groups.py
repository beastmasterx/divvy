"""
API tests for Group endpoints.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models import Group, GroupRole, User
from app.schemas.group import GroupRequest, GroupResponse
from app.schemas.period import PeriodRequest, PeriodResponse
from app.services import AuthorizationService


@pytest.mark.api
class TestGroupsAPI:
    """Test suite for Groups API endpoints."""

    # ============================================================================
    # Helper Fixtures
    # ============================================================================

    @pytest.fixture
    async def owner_user(self, user_factory: Callable[..., Awaitable[User]]) -> User:
        """Create a user who will be an owner of test groups."""
        return await user_factory(email="owner@example.com", name="Owner")

    @pytest.fixture
    async def member_user(self, user_factory: Callable[..., Awaitable[User]]) -> User:
        """Create a user who will be a member of test groups."""
        return await user_factory(email="member@example.com", name="Member")

    @pytest.fixture
    async def admin_user(self, user_factory: Callable[..., Awaitable[User]]) -> User:
        """Create a user who will be an admin of test groups."""
        return await user_factory(email="admin@example.com", name="Admin")

    @pytest.fixture
    async def group_with_owner(
        self,
        owner_user: User,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ) -> Group:
        """Create a group with an owner."""
        return await group_with_role_factory(user_id=owner_user.id, role=GroupRole.OWNER, name="Test Group")

    # ============================================================================
    # GET /groups/ - List user's groups
    # ============================================================================

    async def test_get_groups_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test endpoint requires authentication - returns 401."""
        response = await unauthenticated_async_client.get("/api/v1/groups/", follow_redirects=True)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        error_data = response.json()
        assert "detail" in error_data
        assert "www-authenticate" in response.headers

    async def test_get_groups_returns_user_groups(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        group_factory: Callable[..., Awaitable[Group]],
    ):
        """Test GET returns groups the authenticated user is a member of."""
        # Create groups with owner_user as member
        group1 = await group_with_role_factory(user_id=owner_user.id, role=GroupRole.OWNER, name="Group 1")
        group2 = await group_with_role_factory(user_id=owner_user.id, role=GroupRole.MEMBER, name="Group 2")
        # Create group3 without owner_user (should not appear in results)
        group3 = await group_factory(name="Group 3")

        async for client in async_client_factory(owner_user):
            response = await client.get("/api/v1/groups/", follow_redirects=True)

            assert response.status_code == status.HTTP_200_OK
            data: list[dict[str, Any]] = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

            group_ids = {group["id"] for group in data}
            assert group1.id in group_ids
            assert group2.id in group_ids
            assert group3.id not in group_ids

    async def test_get_groups_returns_empty_list(
        self,
        async_client: AsyncClient,
    ):
        """Test GET returns empty list when user has no groups."""
        response = await async_client.get("/api/v1/groups/", follow_redirects=True)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data == []
        assert isinstance(data, list)

    # ============================================================================
    # GET /groups/{group_id} - Get group by ID
    # ============================================================================

    async def test_get_group_by_id_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
        group_with_owner: Group,
    ):
        """Test endpoint requires authentication."""
        response = await unauthenticated_async_client.get(
            f"/api/v1/groups/{group_with_owner.id}", follow_redirects=True
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_group_by_id_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
    ):
        """Test endpoint requires group membership (returns 404 for non-members for security)."""
        async for client in async_client_factory(member_user):
            response = await client.get(f"/api/v1/groups/{group_with_owner.id}", follow_redirects=True)

            # Returns 404 (not 403) for non-members to avoid revealing group existence (security-by-obscurity)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_group_by_id_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test successful GET returns group data."""
        async for client in async_client_factory(owner_user):
            response = await client.get(f"/api/v1/groups/{group_with_owner.id}", follow_redirects=True)

            assert response.status_code == status.HTTP_200_OK
            group = GroupResponse.model_validate(response.json())
            assert group.id == group_with_owner.id
            assert group.name == group_with_owner.name

    async def test_get_group_by_id_not_found(
        self,
        async_client: AsyncClient,
    ):
        """Test GET returns 404 for non-existent group."""
        response = await async_client.get("/api/v1/groups/99999", follow_redirects=True)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ============================================================================
    # POST /groups/ - Create group
    # ============================================================================

    async def test_create_group_requires_authentication(
        self,
        unauthenticated_async_client: AsyncClient,
    ):
        """Test endpoint requires authentication."""
        request = GroupRequest(name="New Group")
        response = await unauthenticated_async_client.post(
            "/api/v1/groups/",
            json=request.model_dump(),
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_group_success(
        self,
        async_client: AsyncClient,
    ):
        """Test successful group creation."""
        request = GroupRequest(name="New Group")
        response = await async_client.post(
            "/api/v1/groups/",
            json=request.model_dump(),
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_201_CREATED
        group = GroupResponse.model_validate(response.json())
        assert group.id is not None
        assert group.name == "New Group"

    async def test_create_group_creates_owner_role(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        authorization_service: AuthorizationService,
    ):
        """Test creating a group automatically assigns owner role to creator."""
        request = GroupRequest(name="My Group")
        async for client in async_client_factory(owner_user):
            response = await client.post(
                "/api/v1/groups/",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_201_CREATED
            group = GroupResponse.model_validate(response.json())
            group_id = group.id

            # Verify user is owner
            role = await authorization_service.get_group_role_by_group_id(owner_user.id, group_id)
            assert role == GroupRole.OWNER.value

    async def test_create_group_validation_error(
        self,
        async_client: AsyncClient,
    ):
        """Test creating group with invalid data returns 422."""
        response = await async_client.post(
            "/api/v1/groups/",
            json={},  # Missing required 'name' field
            follow_redirects=True,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ============================================================================
    # PUT /groups/{group_id} - Update group
    # ============================================================================

    async def test_update_group_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test update requires owner or admin role."""
        # Add member_user to the group as a MEMBER so they can access the endpoint
        # but will be denied due to insufficient role (expecting 403, not 404)
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        request = GroupRequest(name="Updated Name")
        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_group_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test successful group update."""
        request = GroupRequest(name="Updated Name")
        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            group = GroupResponse.model_validate(response.json())
            assert group.name == "Updated Name"
            assert group.id == group_with_owner.id

    async def test_update_group_as_admin_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        admin_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test admin can update group."""
        # Add admin_user as admin
        await group_with_role_factory(user_id=admin_user.id, role=GroupRole.ADMIN, group_id=group_with_owner.id)

        request = GroupRequest(name="Admin Updated")
        async for client in async_client_factory(admin_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            group = GroupResponse.model_validate(response.json())
            assert group.name == "Admin Updated"

    # ============================================================================
    # DELETE /groups/{group_id} - Delete group
    # ============================================================================

    async def test_delete_group_requires_owner(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test delete requires owner role."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(member_user):
            response = await client.delete(
                f"/api/v1/groups/{group_with_owner.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_group_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test successful group deletion."""
        async for client in async_client_factory(owner_user):
            response = await client.delete(
                f"/api/v1/groups/{group_with_owner.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

            # Verify group is deleted
            get_response = await client.get(
                f"/api/v1/groups/{group_with_owner.id}",
                follow_redirects=True,
            )
            assert get_response.status_code == status.HTTP_404_NOT_FOUND

    # ============================================================================
    # PUT /groups/{group_id}/users/{user_id}/{role} - Assign role
    # ============================================================================

    async def test_assign_role_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        owner_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test assigning role requires owner or admin."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(member_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}/users/{owner_user.id}/group:admin",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_assign_role_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        authorization_service: AuthorizationService,
    ):
        """Test successful role assignment."""
        # Add member_user as member first
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}/group:admin",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

            # Verify role was assigned
            role = await authorization_service.get_group_role_by_group_id(member_user.id, group_with_owner.id)
            assert role == GroupRole.ADMIN.value

    async def test_assign_owner_role_blocked(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test assigning owner role via this endpoint is blocked."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}/group:owner",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    # ============================================================================
    # GET /groups/{group_id}/periods - List periods
    # ============================================================================

    async def test_get_periods_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
    ):
        """Test getting periods requires group membership."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/groups/{group_with_owner.id}/periods",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_periods_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test successful period list retrieval."""
        async for client in async_client_factory(owner_user):
            response = await client.get(
                f"/api/v1/groups/{group_with_owner.id}/periods",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK
            periods = [PeriodResponse.model_validate(item) for item in response.json()]
            assert isinstance(periods, list)
            assert all(isinstance(p, PeriodResponse) for p in periods)

    # ============================================================================
    # PUT /groups/{group_id}/users/{user_id} - Transfer ownership
    # ============================================================================

    async def test_transfer_ownership_requires_owner(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        admin_user: User,
        owner_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test transferring ownership requires owner role."""
        # Add admin_user as admin
        await group_with_role_factory(user_id=admin_user.id, role=GroupRole.ADMIN, group_id=group_with_owner.id)

        async for client in async_client_factory(admin_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}/users/{admin_user.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_transfer_ownership_requires_target_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
    ):
        """Test transferring ownership requires target user to be a member."""
        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT  # BusinessRuleError

    async def test_transfer_ownership_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        authorization_service: AuthorizationService,
    ):
        """Test successful ownership transfer."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(owner_user):
            response = await client.put(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify ownership was transferred
            new_owner_role = await authorization_service.get_group_role_by_group_id(member_user.id, group_with_owner.id)
            old_owner_role = await authorization_service.get_group_role_by_group_id(owner_user.id, group_with_owner.id)
            assert new_owner_role == GroupRole.OWNER.value
            assert old_owner_role == GroupRole.MEMBER.value

    # ============================================================================
    # DELETE /groups/{group_id}/users/{user_id} - Remove user
    # ============================================================================

    async def test_remove_user_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test removing user requires owner or admin role - members cannot remove users."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(member_user):
            response = await client.delete(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_remove_user_as_admin_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        admin_user: User,
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        authorization_service: AuthorizationService,
    ):
        """Test admin can successfully remove users from group."""
        # Add users
        await group_with_role_factory(user_id=admin_user.id, role=GroupRole.ADMIN, group_id=group_with_owner.id)
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(admin_user):
            response = await client.delete(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

            # Verify user was removed
            role = await authorization_service.get_group_role_by_group_id(member_user.id, group_with_owner.id)
            assert role is None

    async def test_remove_user_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
        authorization_service: AuthorizationService,
    ):
        """Test successful user removal."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        async for client in async_client_factory(owner_user):
            response = await client.delete(
                f"/api/v1/groups/{group_with_owner.id}/users/{member_user.id}",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_204_NO_CONTENT

            # Verify user was removed
            role = await authorization_service.get_group_role_by_group_id(member_user.id, group_with_owner.id)
            assert role is None

    # ============================================================================
    # GET /groups/{group_id}/periods/current - Get current period
    # ============================================================================

    async def test_get_current_period_requires_membership(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test getting current period requires membership - non-members get 404."""
        async for client in async_client_factory(member_user):
            response = await client.get(
                f"/api/v1/groups/{group_with_owner.id}/periods/current",
                follow_redirects=True,
            )

            # Non-members get 404 (security-by-obscurity pattern)
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_current_period_not_found(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test getting current period when none exists returns 404."""
        async for client in async_client_factory(owner_user):
            response = await client.get(
                f"/api/v1/groups/{group_with_owner.id}/periods/current",
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    # ============================================================================
    # POST /groups/{group_id}/periods - Create period
    # ============================================================================

    async def test_create_period_requires_owner_or_admin(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        member_user: User,
        group_with_owner: Group,
        group_with_role_factory: Callable[..., Awaitable[Group]],
    ):
        """Test creating period requires owner or admin role."""
        # Add member_user as member
        await group_with_role_factory(user_id=member_user.id, role=GroupRole.MEMBER, group_id=group_with_owner.id)

        request = PeriodRequest(name="New Period")
        async for client in async_client_factory(member_user):
            response = await client.post(
                f"/api/v1/groups/{group_with_owner.id}/periods",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_period_success(
        self,
        async_client_factory: Callable[[User], AsyncIterator[AsyncClient]],
        owner_user: User,
        group_with_owner: Group,
    ):
        """Test successful period creation."""
        request = PeriodRequest(name="New Period")
        async for client in async_client_factory(owner_user):
            response = await client.post(
                f"/api/v1/groups/{group_with_owner.id}/periods",
                json=request.model_dump(),
                follow_redirects=True,
            )

            assert response.status_code == status.HTTP_201_CREATED
            period = PeriodResponse.model_validate(response.json())
            assert period.id is not None
            assert period.name == "New Period"
