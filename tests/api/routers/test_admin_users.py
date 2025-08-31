"""
Tests for the admin user management endpoints.
"""
import pytest
from uuid import UUID
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user import User, SubscriptionStatus
from app.repositories.user import UserRepository
from app.schemas.admin_user import AdminUserUpdate


class TestAdminUserEndpoints:
    """Test class for admin user management endpoints."""

    def test_get_all_users(self, client, admin_auth_headers, db_session):
        """Test getting all users as admin."""
        # Act - get users
        response = client.get(
            "/api/admin/users",
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure - it should be a list of users
        assert isinstance(data, list)
        
        # Check that we have at least our seeded users
        assert len(data) >= 4  # We should have seeded users from the fixtures
        
        # Verify user fields
        for user in data:
            assert "id" in user
            assert "email" in user
            assert "is_admin" in user
            assert "is_active" in user
            assert "subscription_status" in user

    def test_get_users_with_filters(self, client, admin_auth_headers, db_session):
        """Test getting users with filters."""
        # Act - get admin users
        response = client.get(
            "/api/admin/users?is_admin=true",
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # All returned users should be admin users
        for user in data:
            assert user["is_admin"] == True
        
        # Test another filter - inactive users
        response = client.get(
            "/api/admin/users?is_active=false",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned users should be inactive
        for user in data:
            assert user["is_active"] == False

    def test_get_users_with_search(self, client, admin_auth_headers, db_session):
        """Test searching for users."""
        # Act - search for 'admin' in email
        response = client.get(
            "/api/admin/users?search=admin",
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # All returned users should have 'admin' in their email
        for user in data:
            assert "admin" in user["email"].lower()

    def test_get_user_detail(self, client, admin_auth_headers, db_session):
        """Test getting detailed user information."""
        # Arrange - get a user ID first
        user_repo = UserRepository(db_session)
        user = user_repo.get_by_email("user@example.com")
        assert user is not None
        
        # Act - get user detail
        response = client.get(
            f"/api/admin/users/{user.id}",
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify user data
        assert data["id"] == str(user.id)
        assert data["email"] == "user@example.com"
        assert data["is_admin"] == False
        assert data["is_active"] == True

    def test_get_nonexistent_user(self, client, admin_auth_headers):
        """Test getting a nonexistent user."""
        # Act - get nonexistent user
        response = client.get(
            f"/api/admin/users/00000000-0000-0000-0000-000000000000",
            headers=admin_auth_headers
        )
        
        # Assert
        assert response.status_code == 404
        detail = response.json().get("detail", "")
        if isinstance(detail, dict):
            detail = detail.get("message", "")
        assert "not found" in str(detail).lower()

    def test_update_user(self, client, admin_auth_headers, db_session):
        """Test updating a user."""
        # Arrange - get a user ID first
        user_repo = UserRepository(db_session)
        user = user_repo.get_by_email("user@example.com")
        assert user is not None
        
        # Store original values
        original_name = user.full_name
        new_name = "Updated Test User"
        
        # Act - update user
        response = client.patch(
            f"/api/admin/users/{user.id}",
            headers=admin_auth_headers,
            json={"full_name": new_name}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify user data was updated
        assert data["full_name"] == new_name
        
        # Verify in database
        db_session.refresh(user)
        assert user.full_name == new_name
        
        # Clean up - restore original values
        user.full_name = original_name
        db_session.add(user)
        db_session.commit()

    def test_update_subscription_status(self, client, admin_auth_headers, db_session):
        """Test updating a user's subscription status."""
        # Arrange - get a user ID first
        user_repo = UserRepository(db_session)
        user = user_repo.get_by_email("user@example.com")
        assert user is not None
        
        # Store original status
        original_status = user.subscription_status
        new_status = SubscriptionStatus.paused
        
        # Act - update subscription status
        response = client.patch(
            f"/api/admin/users/{user.id}",
            headers=admin_auth_headers,
            json={"subscription_status": new_status.value}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify status was updated
        assert data["subscription_status"] == new_status.value
        
        # Verify in database
        db_session.refresh(user)
        assert user.subscription_status == new_status
        
        # Clean up - restore original status
        user.subscription_status = original_status
        db_session.add(user)
        db_session.commit()

    def test_toggle_admin_status(self, client, admin_auth_headers, db_session):
        """Test toggling admin status."""
        # Arrange - get a non-admin user ID
        user_repo = UserRepository(db_session)
        user = user_repo.get_by_email("user@example.com")
        assert user is not None
        assert user.is_admin == False
        
        # Act - make user an admin
        response = client.post(
            f"/api/admin/users/{user.id}/toggle-admin",
            headers=admin_auth_headers,
            params={"make_admin": True}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify admin status was updated
        assert data["is_admin"] == True
        
        # Verify in database
        db_session.refresh(user)
        assert user.is_admin == True
        
        # Act - remove admin status
        response = client.post(
            f"/api/admin/users/{user.id}/toggle-admin",
            headers=admin_auth_headers,
            params={"make_admin": False}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify admin status was updated
        assert data["is_admin"] == False
        
        # Verify in database
        db_session.refresh(user)
        assert user.is_admin == False

    def test_toggle_active_status(self, client, admin_auth_headers, db_session):
        """Test toggling active status."""
        # Arrange - get an active user ID
        user_repo = UserRepository(db_session)
        user = user_repo.get_by_email("user@example.com")
        assert user is not None
        assert user.is_active == True
        
        # Act - deactivate user
        response = client.post(
            f"/api/admin/users/{user.id}/toggle-active",
            headers=admin_auth_headers,
            params={"make_active": False}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify active status was updated
        assert data["is_active"] == False
        
        # Verify in database
        db_session.refresh(user)
        assert user.is_active == False
        
        # Act - reactivate user
        response = client.post(
            f"/api/admin/users/{user.id}/toggle-active",
            headers=admin_auth_headers,
            params={"make_active": True}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify active status was updated
        assert data["is_active"] == True
        
        # Verify in database
        db_session.refresh(user)
        assert user.is_active == True

    def test_cant_toggle_own_admin_status(self, client, admin_auth_headers, db_session):
        """Test that admins can't remove their own admin status."""
        # Arrange - get current admin user ID
        user_repo = UserRepository(db_session)
        user = user_repo.get_by_email("admin@example.com")
        assert user is not None
        assert user.is_admin == True
        
        # Act - try to remove own admin status
        response = client.post(
            f"/api/admin/users/{user.id}/toggle-admin",
            headers=admin_auth_headers,
            params={"make_admin": False}
        )
        
        # Assert
        assert response.status_code == 400
        detail = response.json().get("detail", "")
        if isinstance(detail, dict):
            detail = detail.get("message", "")
        assert "cannot remove your own admin privileges" in str(detail).lower()
        
        # Verify status didn't change in database
        db_session.refresh(user)
        assert user.is_admin == True

    def test_non_admin_access_denied(self, client, user_auth_headers):
        """Test that non-admin users can't access admin endpoints."""
        # Act - try to access admin endpoint with non-admin user
        response = client.get(
            "/api/admin/users",
            headers=user_auth_headers
        )
        
        # Assert
        assert response.status_code == 403
        detail = response.json().get("detail", "")
        if isinstance(detail, dict):
            detail = detail.get("message", "")
        assert "privileges" in str(detail).lower()
