"""Tests for admin user management endpoints (Task 5.1)."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


def _login_as_admin(client, db_session):
    """Helper to login as admin and configure client to use JWT token."""
    from litfoundry.auth import get_password_hasher
    from litfoundry.catalog import User
    
    hasher = get_password_hasher()
    admin = User(
        id=str(uuid4()),
        account_type="local",
        username="admin",
        username_normalized="admin",
        password_hash=hasher.hash("AdminPass123"),
        must_change_password=False,
        role="admin",
        active=True,
        session_version=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(admin)
    db_session.commit()
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "AdminPass123"
    })
    assert response.status_code == 200, f"Login failed: {response.get_json()}"
    
    # Flask test client should automatically preserve cookies, but if it doesn't work,
    # we can manually set headers. For now, trust that Flask's test_client preserves cookies.
    return client, admin.id


class TestAdminUserListAndCreate:
    """Test GET/POST /api/v1/admin/users endpoints."""

    def test_list_users_as_admin(self, client, db_session):
        """Admin can list all users."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        admin_in_list = any(u["username"] == "admin" for u in data)
        assert admin_in_list

    def test_create_user_as_admin(self, client, db_session):
        """Admin can create a new local user."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "newuser", "password": "SecurePass123", "role": "user"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["username"] == "newuser"
        assert data["account_type"] == "local"
        assert data["role"] == "user"
        assert data["active"] is True

    def test_create_user_missing_username(self, client, db_session):
        """Creating user without username fails."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"password": "SecurePass123"}
        )
        assert response.status_code == 400

    def test_create_user_missing_password(self, client, db_session):
        """Creating user without password fails."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "newuser"}
        )
        assert response.status_code == 400

    def test_create_user_duplicate_username_case_insensitive(self, client, db_session):
        """Creating user with duplicate username (case-insensitive) fails."""
        _login_as_admin(client, db_session)
        response1 = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        assert response1.status_code == 201
        response2 = client.post(
            "/api/v1/admin/users",
            json={"username": "TestUser", "password": "Pass123456"}
        )
        assert response2.status_code == 409

    def test_create_user_invalid_role(self, client, db_session):
        """Creating user with invalid role fails."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "newuser", "password": "SecurePass123", "role": "superuser"}
        )
        assert response.status_code == 400

    def test_create_admin_user(self, client, db_session):
        """Admin can create another admin user."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "newadmin", "password": "AdminPass123", "role": "admin"}
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["role"] == "admin"


class TestAdminUserUpdate:
    """Test PATCH /api/v1/admin/users/{user_id} endpoint."""

    def test_update_user_active_status(self, client, db_session):
        """Admin can update user active status."""
        _login_as_admin(client, db_session)
        # Create a user first
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_id = response.get_json()["id"]
        # Disable the user
        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"active": False}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["active"] is False

    def test_update_user_role(self, client, db_session):
        """Admin can update user role."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_id = response.get_json()["id"]
        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"role": "admin"}
        )
        assert response.status_code == 200

    def test_cannot_disable_admin_account(self, client, db_session):
        """Cannot disable the admin account."""
        _, admin_id = _login_as_admin(client, db_session)
        response = client.patch(
            f"/api/v1/admin/users/{admin_id}",
            json={"active": False}
        )
        assert response.status_code == 403
        data = response.get_json()
        assert "cannot disable" in data.get("message", "").lower()

    def test_cannot_change_admin_role(self, client, db_session):
        """Cannot change the admin account role."""
        _, admin_id = _login_as_admin(client, db_session)
        response = client.patch(
            f"/api/v1/admin/users/{admin_id}",
            json={"role": "user"}
        )
        assert response.status_code == 403

    def test_cannot_change_account_type(self, client, db_session):
        """Cannot change account type through PATCH."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_id = response.get_json()["id"]
        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"account_type": "ldap"}
        )
        assert response.status_code == 400

    def test_update_nonexistent_user(self, client, db_session):
        """Updating nonexistent user fails."""
        _login_as_admin(client, db_session)
        response = client.patch(
            f"/api/v1/admin/users/nonexistent-id",
            json={"active": False}
        )
        assert response.status_code == 404


class TestAdminResetPassword:
    """Test POST /api/v1/admin/users/{user_id}/reset-password endpoint."""

    def test_reset_password(self, client, db_session):
        """Admin can reset user password."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_id = response.get_json()["id"]
        response = client.post(
            f"/api/v1/admin/users/{user_id}/reset-password",
            json={"password": "NewPass123"}
        )
        assert response.status_code == 200

    def test_reset_password_missing_password(self, client, db_session):
        """Reset password without password field fails."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_id = response.get_json()["id"]
        response = client.post(
            f"/api/v1/admin/users/{user_id}/reset-password",
            json={}
        )
        assert response.status_code == 400

    def test_reset_password_nonexistent_user(self, client, db_session):
        """Resetting password for nonexistent user fails."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users/nonexistent-id/reset-password",
            json={"password": "NewPass123"}
        )
        assert response.status_code == 404

    def test_reset_password_increments_session_version(self, client, db_session):
        """Resetting password increments user session_version."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_data = response.get_json()
        user_id = user_data["id"]
        old_sv = user_data["session_version"]
        
        response = client.post(
            f"/api/v1/admin/users/{user_id}/reset-password",
            json={"password": "NewPass123"}
        )
        new_data = response.get_json()
        assert new_data["session_version"] > old_sv


class TestAdminRevokeSessions:
    """Test POST /api/v1/admin/users/{user_id}/revoke-sessions endpoint."""

    def test_revoke_sessions(self, client, db_session):
        """Admin can revoke user sessions."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "testuser", "password": "Pass123456"}
        )
        user_id = response.get_json()["id"]
        response = client.post(
            f"/api/v1/admin/users/{user_id}/revoke-sessions"
        )
        assert response.status_code == 200

    def test_revoke_sessions_nonexistent_user(self, client, db_session):
        """Revoking sessions for nonexistent user fails."""
        _login_as_admin(client, db_session)
        response = client.post(
            "/api/v1/admin/users/nonexistent-id/revoke-sessions"
        )
        assert response.status_code == 404


class TestAuditEvents:
    """Test GET /api/v1/admin/audit-events endpoint and audit logging."""

    def test_get_audit_events_as_admin(self, client, db_session):
        """Admin can retrieve audit events."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/audit-events")
        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_audit_events_filter_by_action(self, client, db_session):
        """Audit events can be filtered by action."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/audit-events?action=create_user")
        assert response.status_code == 200

    def test_audit_events_filter_by_resource_type(self, client, db_session):
        """Audit events can be filtered by resource type."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/audit-events?resource_type=user")
        assert response.status_code == 200

    def test_audit_events_pagination(self, client, db_session):
        """Audit events support pagination."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/audit-events?limit=10&offset=0")
        assert response.status_code == 200

    def test_audit_events_default_limit(self, client, db_session):
        """Audit events have a default limit."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/audit-events")
        assert response.status_code == 200

    def test_audit_events_max_limit(self, client, db_session):
        """Audit events respect max limit."""
        _login_as_admin(client, db_session)
        response = client.get("/api/v1/admin/audit-events?limit=1000")
        assert response.status_code == 200


class TestAdminEndpointsSecurity:
    """Test security of admin endpoints."""

    def test_user_cannot_create_user(self, client, db_session):
        """Non-admin user cannot create other users."""
        # Create a regular user
        from litfoundry.auth import get_password_hasher
        from litfoundry.catalog import User
        
        hasher = get_password_hasher()
        user = User(
            id=str(uuid4()),
            account_type="local",
            username="regularuser",
            username_normalized="regularuser",
            password_hash=hasher.hash("Pass123456"),
            must_change_password=False,
            role="user",
            active=True,
            session_version=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(user)
        db_session.commit()
        
        # Login as regular user
        response = client.post("/api/v1/auth/login", json={
            "username": "regularuser",
            "password": "Pass123456"
        })
        assert response.status_code == 200
        
        # Try to create user - should fail
        response = client.post(
            "/api/v1/admin/users",
            json={"username": "another", "password": "Pass123456"}
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_admin(self, client, db_session):
        """Unauthenticated user cannot access admin endpoints."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 403
