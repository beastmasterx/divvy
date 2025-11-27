"""
API tests for Category endpoints.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.models import Category


@pytest.mark.api
class TestCategoriesAPI:
    """Test suite for Categories API endpoints."""

    # ============================================================================
    # Priority 1: Critical Test Cases
    # ============================================================================

    async def test_get_all_categories_requires_authentication(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test endpoint requires authentication - returns 401 (OAuth2 standard)."""
        # Use trailing slash to match route definition @router.get("/")
        response = await unauthenticated_client.get("/api/v1/categories/", follow_redirects=True)

        # OAuth2 RFC 6749 standard: 401 Unauthorized for missing/invalid tokens
        assert response.status_code == 401
        # Verify error response format
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)
        # Verify WWW-Authenticate header is present (OAuth2 requirement)
        assert "www-authenticate" in response.headers
        assert "Bearer" in response.headers.get("www-authenticate", "")

    async def test_get_all_categories_returns_categories(
        self,
        async_client: AsyncClient,
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test successful GET returns 200 with category data."""
        category = await category_factory(name="Food", is_default=False)

        response = await async_client.get("/api/v1/categories/", follow_redirects=True)

        assert response.status_code == 200
        data: list[dict[str, Any]] = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == category.id
        assert data[0]["name"] == "Food"
        assert data[0]["is_default"] is False

    async def test_get_all_categories_returns_empty_list(
        self,
        async_client: AsyncClient,
    ):
        """Test GET with no categories returns 200 with empty list."""
        response = await async_client.get("/api/v1/categories/", follow_redirects=True)

        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert isinstance(data, list)

    # ============================================================================
    # Priority 2: Important Test Cases
    # ============================================================================

    async def test_get_all_categories_response_schema(
        self,
        async_client: AsyncClient,
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test response matches CategoryResponse schema."""
        await category_factory(name="Transportation", is_default=False)

        response = await async_client.get("/api/v1/categories/", follow_redirects=True)

        assert response.status_code == 200
        data: list[dict[str, Any]] = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

        category = data[0]
        # Verify all required fields from CategoryResponse schema
        assert "id" in category
        assert "name" in category
        assert "is_default" in category

        # Verify data types
        assert isinstance(category["id"], int)
        assert isinstance(category["name"], str)
        assert isinstance(category["is_default"], bool)

    async def test_get_all_categories_returns_all_categories(
        self,
        async_client: AsyncClient,
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test endpoint returns all categories, not a subset."""
        await category_factory(name="Food")
        await category_factory(name="Transportation")
        await category_factory(name="Entertainment")

        response = await async_client.get("/api/v1/categories/", follow_redirects=True)
        data: list[dict[str, Any]] = response.json()

        assert response.status_code == 200
        assert len(data) == 3

        # Verify all categories are present
        category_names = {cat["name"] for cat in data}
        assert "Food" in category_names
        assert "Transportation" in category_names
        assert "Entertainment" in category_names

    async def test_get_all_categories_ordered_by_id(
        self,
        async_client: AsyncClient,
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test categories are returned ordered by ID (as documented)."""
        # Create in non-sequential order
        await category_factory(name="Second")
        await category_factory(name="First")
        await category_factory(name="Third")

        response = await async_client.get("/api/v1/categories/", follow_redirects=True)
        data: list[dict[str, Any]] = response.json()

        assert response.status_code == 200
        assert len(data) == 3

        # Verify IDs are in ascending order
        ids = [cat["id"] for cat in data]
        assert ids == sorted(ids)

        # Verify names are present (order may vary by ID)
        names = {cat["name"] for cat in data}
        assert names == {"First", "Second", "Third"}

    # ============================================================================
    # Priority 3: Nice to Have Test Cases
    # ============================================================================

    async def test_get_all_categories_content_type(
        self,
        async_client: AsyncClient,
    ):
        """Test response has correct Content-Type header."""
        response = await async_client.get("/api/v1/categories/", follow_redirects=True)

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "").lower()

    async def test_get_all_categories_includes_default_flag(
        self,
        async_client: AsyncClient,
        category_factory: Callable[..., Awaitable[Category]],
    ):
        """Test response includes correct is_default values."""
        await category_factory(name="Default", is_default=True)
        await category_factory(name="Custom", is_default=False)

        response = await async_client.get("/api/v1/categories/", follow_redirects=True)
        data: list[dict[str, Any]] = response.json()

        assert response.status_code == 200
        assert len(data) == 2

        # Find categories by name
        default = next(c for c in data if c["name"] == "Default")
        custom = next(c for c in data if c["name"] == "Custom")

        assert default["is_default"] is True
        assert custom["is_default"] is False

    async def test_get_all_categories_rejects_invalid_token(
        self,
        app: FastAPI,
    ):
        """Test endpoint rejects invalid authentication tokens."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/categories/",
                headers={"Authorization": "Bearer invalid_token_123"},
                follow_redirects=True,
            )

        assert response.status_code == 401
        error_data = response.json()
        assert "detail" in error_data
        assert isinstance(error_data["detail"], str)
