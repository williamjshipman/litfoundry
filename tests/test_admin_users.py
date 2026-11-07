"""Tests for admin user management endpoints (Task 5.1)."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


class TestAdminUserListAndCreate:
    """Test GET/POST /api/v1/admin/users endpoints."""

    def test_list_users_as_admin(self, client, admin_user_local):
        """Admin can list all users."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Should contain the admin user
        admin_in_list = any(u["username"] == "admin" for u in data)
        assert admin_in_list

    def test_create_user_as_admin(self, client, admin_user_local):
        """Admin can create a new local user."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "username": "newuser",
                "password": "SecurePass123",
                "role": "user"
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["username"] == "newuser"
        assert data["account_type"] == "local"
        assert data["role"] == "user"
        assert data["active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_user_missing_username(self, client, admin_user_local):
        """Creating user without username fails."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "password": "SecurePass123"
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "username is required" in data.get("message", "")

    def test_create_user_missing_password(self, client, admin_user_local):
        """Creating user without password fails."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "username": "newuser"
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "password is required" in data.get("message", "")

    def test_create_user_duplicate_username_case_insensitive(self, client, admin_user_local):
        """Creating user with duplicate username (case-insensitive) fails."""
        # Create first user
        response1 = client.post(
            "/api/v1/admin/users",
            json={
                "username": "testuser",
                "password": "Pass123456"
            }
        )
        assert response1.status_code == 201

        # Try to create another with different case
        response2 = client.post(
            "/api/v1/admin/users",
            json={
                "username": "TestUser",
                "password": "Pass123456"
            }
        )
        assert response2.status_code == 409
        data = response2.get_json()
        assert "already exists" in data.get("message", "").lower()

    def test_create_user_invalid_role(self, client, admin_user_local):
        """Creating user with invalid role fails."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "username": "newuser",
                "password": "SecurePass123",
                "role": "superuser"
            }
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "admin" in data.get("message", "").lower() or "user" in data.get("message", "").lower()

    def test_create_admin_user(self, client, admin_user_local):
        """Admin can create another admin user."""
        response = client.post(
            "/api/v1/admin/users",
            json={
                "username": "newadmin",
                "password": "AdminPass123",
                "role": "admin"
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["role"] == "admin"


class TestAdminUserUpdate:
    """Test PATCH /api/v1/admin/users/<user_id> endpoint."""

    def test_update_user_active_status(self, client, admin_user_local, local_user):
        """Admin can enable/disable a user."""
        user_id = local_user.id

        # Disable user
        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"active": False}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["active"] is False

        # Re-enable user
        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"active": True}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["active"] is True

    def test_update_user_role(self, client, admin_user_local, local_user):
        """Admin can change user role."""
        user_id = local_user.id

        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"role": "admin"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["role"] == "admin"

    def test_cannot_disable_admin_account(self, client, admin_user_local):
        """Cannot disable the admin account."""
        admin_id = admin_user_local.id

        response = client.patch(
            f"/api/v1/admin/users/{admin_id}",
            json={"active": False}
        )
        assert response.status_code == 403
        data = response.get_json()
        assert "cannot disable" in data.get("message", "").lower()

    def test_cannot_change_admin_role(self, client, admin_user_local):
        """Cannot change the admin account role."""
        admin_id = admin_user_local.id

        response = client.patch(
            f"/api/v1/admin/users/{admin_id}",
            json={"role": "user"}
        )
        assert response.status_code == 403
        data = response.get_json()
        assert "cannot change role" in data.get("message", "").lower()

    def test_cannot_change_account_type(self, client, admin_user_local, local_user):
        """Cannot change account_type through PATCH."""
        user_id = local_user.id

        response = client.patch(
            f"/api/v1/admin/users/{user_id}",
            json={"account_type": "directory"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "account_type" in data.get("message", "").lower()

    def test_update_nonexistent_user(self, client, admin_user_local):
        """Updating nonexistent user returns 404."""
        fake_id = str(uuid4())

        response = client.patch(
            f"/api/v1/admin/users/{fake_id}",
            json={"active": False}
        )
        assert response.status_code == 404


class TestAdminResetPassword:
    """Test POST /api/v1/admin/users/<user_id>/reset-password endpoint."""

    def test_reset_password(self, client, admin_user_local, local_user):
        """Admin can reset a user's password."""
        user_id = local_user.id

        response = client.post(
            f"/api/v1/admin/users/{user_id}/reset-password",
            json={"password": "NewSecurePass123"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == user_id
        assert "id" in data

    def test_reset_password_missing_password(self, client, admin_user_local, local_user):
        """Reset password requires password field."""
        user_id = local_user.id

        response = client.post(
            f"/api/v1/admin/users/{user_id}/reset-password",
            json={}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "password is required" in data.get("message", "")

    def test_reset_password_nonexistent_user(self, client, admin_user_local):
        """Reset password for nonexistent user returns 404."""
        fake_id = str(uuid4())

        response = client.post(
            f"/api/v1/admin/users/{fake_id}/reset-password",
            json={"password": "NewSecurePass123"}
        )
        assert response.status_code == 404

    def test_reset_password_increments_session_version(self, client, admin_user_local, local_user, db_session):
        """Resetting password increments session_version, invalidating sessions."""
        user_id = local_user.id
        old_version = local_user.session_version

        response = client.post(
            f"/api/v1/admin/users/{user_id}/reset-password",
            json={"password": "NewSecurePass123"}
        )
        assert response.status_code == 200

        # Verify session_version incremented
        db_session.refresh(local_user)
        assert local_user.session_version > old_version


class TestAdminRevokeSessions:
    """Test POST /api/v1/admin/users/<user_id>/revoke-sessions endpoint."""

    def test_revoke_sessions(self, client, admin_user_local, local_user, db_session):
        """Admin can revoke all sessions for a user."""
        user_id = local_user.id
        old_version = local_user.session_version

        response = client.post(
            f"/api/v1/admin/users/{user_id}/revoke-sessions"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == user_id

        # Verify session_version incremented
        db_session.refresh(local_user)
        assert local_user.session_version > old_version

    def test_revoke_sessions_nonexistent_user(self, client, admin_user_local):
        """Revoking sessions for nonexistent user returns 404."""
        fake_id = str(uuid4())

        response = client.post(
            f"/api/v1/admin/users/{fake_id}/revoke-sessions"
        )
        assert response.status_code == 404


class TestAuditEvents:
    """Test GET /api/v1/admin/audit-events endpoint."""

    def test_get_audit_events_as_admin(self, client, admin_user_local):
        """Admin can retrieve audit events."""
        # First create a user to generate an audit event
        client.post(
            "/api/v1/admin/users",
            json={
                "username": "audituser",
                "password": "Pass123456"
            }
        )

        response = client.get("/api/v1/admin/audit-events")
        assert response.status_code == 200
        data = response.get_json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)

    def test_audit_events_filter_by_action(self, client, admin_user_local):
        """Audit events can be filtered by action."""
        # Create a user
        client.post(
            "/api/v1/admin/users",
            json={
                "username": "filteruser",
                "password": "Pass123456"
            }
        )

        response = client.get("/api/v1/admin/audit-events?action=create_user")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["events"]) >= 1
        # All events should be create_user
        for event in data["events"]:
            assert event["action"] == "create_user"

    def test_audit_events_filter_by_resource_type(self, client, admin_user_local):
        """Audit events can be filtered by resource type."""
        response = client.get("/api/v1/admin/audit-events?resource_type=user")
        assert response.status_code == 200
        data = response.get_json()
        if len(data["events"]) > 0:
            for event in data["events"]:
                assert event["resource_type"] == "user"

    def test_audit_events_pagination(self, client, admin_user_local):
        """Audit events support pagination with limit and offset."""
        # Create several users to generate events
        for i in range(5):
            client.post(
                "/api/v1/admin/users",
                json={
                    "username": f"paginuser{i}",
                    "password": "Pass123456"
                }
            )

        # Get first page
        response1 = client.get("/api/v1/admin/audit-events?limit=2&offset=0")
        assert response1.status_code == 200
        data1 = response1.get_json()
        assert len(data1["events"]) <= 2

        # Get second page
        response2 = client.get("/api/v1/admin/audit-events?limit=2&offset=2")
        assert response2.status_code == 200
        data2 = response2.get_json()
        assert len(data2["events"]) <= 2

        # Ensure different results
        if len(data1["events"]) > 0 and len(data2["events"]) > 0:
            assert data1["events"][0]["id"] != data2["events"][0]["id"]

    def test_audit_events_default_limit(self, client, admin_user_local):
        """Audit events have a default limit of 100."""
        response = client.get("/api/v1/admin/audit-events")
        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 100

    def test_audit_events_max_limit(self, client, admin_user_local):
        """Audit events limit is capped at 1000."""
        response = client.get("/api/v1/admin/audit-events?limit=5000")
        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 1000


class TestAdminEndpointsSecurity:
    """Test that admin endpoints are properly secured."""

    def test_user_cannot_create_user(self, client, local_user):
        """Non-admin user cannot create users."""
        # Login as local_user (not admin)
        client.post(
            "/api/v1/auth/login",
            json={
                "username": local_user.username,
                "password": "TestPass123"
            }
        )

        response = client.post(
            "/api/v1/admin/users",
            json={
                "username": "newuser",
                "password": "Pass123456"
            }
        )
        # Should be 403 or 401 (permission denied or not authenticated)
        assert response.status_code in [401, 403]

    def test_unauthenticated_cannot_access_admin(self, client):
        """Unauthenticated user cannot access admin endpoints."""
        response = client.get("/api/v1/admin/users")
        assert response.status_code in [401, 403]


# Fixtures
@pytest.fixture
def local_user(app, admin_user_local, db_session):
    """Create a test local user."""
    from litfoundry.auth import get_password_hasher
    from litfoundry.catalog import User
    from datetime import datetime, timezone
    from uuid import uuid4

    hasher = get_password_hasher()
    user = User(
        id=str(uuid4()),
        account_type="local",
        username="testuser",
        username_normalized="testuser",
        password_hash=hasher.hash("TestPass123"),
        must_change_password=False,
        role="user",
        active=True,
        session_version=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
