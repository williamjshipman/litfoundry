"""Quick test to verify JWT persistence in admin_user_local fixture."""

import pytest


class TestJWTPersistence:
    """Test that JWT tokens are persisted correctly."""

    def test_admin_user_has_jwt_after_login(self, client, admin_user_local):
        """Admin user should have valid JWT after fixture login."""
        # The fixture already logged in, so cookies should be set
        # Try to access a protected endpoint
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200, f"Failed to access /auth/me: {response.get_json()}"
        data = response.get_json()
        assert data["id"] == admin_user_local.id
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_admin_list_users_endpoint(self, client, admin_user_local):
        """Admin should be able to list users with valid JWT."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 200, f"Failed to list users: {response.get_json()}"
        users = response.get_json()
        assert isinstance(users, list)
        assert any(u["username"] == "admin" for u in users)
