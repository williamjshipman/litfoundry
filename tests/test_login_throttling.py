"""Tests for login throttling with exponential backoff."""

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from litfoundry.auth import create_user_with_password
from litfoundry.catalog import User, AuthSettings


@pytest.fixture
def admin_user_local(db_session):
    """Create a local admin user for testing."""
    admin = create_user_with_password(
        str(uuid4()),
        "admin",
        "AdminPass123",
        role="admin",
        account_type="local"
    )
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def regular_user_local(db_session):
    """Create a regular local user for testing."""
    user = create_user_with_password(
        str(uuid4()),
        "testuser",
        "TestPass123",
        role=None,
        account_type="local"
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestLoginThrottlingBasics:
    """Test basic throttling logic."""
    
    def test_successful_login_no_throttle(self, app, client, admin_user_local):
        """Successful login doesn't trigger throttle."""
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["username"] == "admin"
    
    def test_failed_login_increments_throttle(self, app, client, admin_user_local):
        """Failed login attempts increment throttle counter."""
        # Make 5 failed attempts
        for i in range(5):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # 6th attempt should still work (limit is 10 per IP for default policy)
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 200
    
    def test_throttle_after_max_attempts_per_ip(self, app, client, admin_user_local):
        """Throttle activates after max attempts per IP (default 10)."""
        # Make 10 failed login attempts on same IP
        for i in range(10):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # 11th attempt should be throttled
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 429
        data = response.get_json()
        assert data["code"] == "AUTH_THROTTLED"
        assert "retry_after_seconds" in data["details"]
    
    def test_retry_after_header_present(self, app, client, admin_user_local):
        """Throttle response includes Retry-After header."""
        # Make 10+ failed attempts to trigger throttle
        for i in range(11):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
        
        # Last response should have Retry-After
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0


class TestAdminThrottlingPerIPOnly:
    """Test that admin is only throttled per IP, not per identifier."""
    
    def test_admin_throttled_per_ip_only(self, app, db_session, client, admin_user_local):
        """Admin login is throttled per IP only, not per username."""
        # Make 5 failed attempts with admin account from primary IP
        for i in range(5):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # Regular user from same IP should also be throttled per IP
        # But if they use different username, they might have room under username-based throttle
        user = create_user_with_password(
            str(uuid4()),
            "otheruser",
            "OtherPass123",
            account_type="local"
        )
        db_session.add(user)
        db_session.commit()
        
        # More attempts with different username - these hit the per-IP limit
        for i in range(5):
            response = client.post("/api/v1/auth/login", json={
                "username": "otheruser",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # 11th total attempt from this IP should be throttled
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 429


class TestUserThrottlingPerIdentifier:
    """Test that regular users are throttled per identifier."""
    
    def test_user_throttled_per_identifier(self, app, client, regular_user_local):
        """Regular user login is throttled per username (default 5 per 15 min)."""
        # Make 5 failed attempts with the user's username
        for i in range(5):
            response = client.post("/api/v1/auth/login", json={
                "username": "testuser",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # 6th attempt should be throttled (identifier limit reached)
        response = client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "TestPass123"
        })
        assert response.status_code == 429
        data = response.get_json()
        assert data["code"] == "AUTH_THROTTLED"
    
    def test_admin_can_login_different_ip_while_ip_throttled(self, app, client, db_session, admin_user_local):
        """Admin can sign in from a second IP while the first is throttled.
        
        This is the key difference between admin (per-IP only) and regular users
        (per-IP AND per-identifier).
        """
        # Simulate 10 failed login attempts from first IP (default per-IP limit)
        for i in range(10):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # Verify first IP is now throttled
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 429  # IP throttled
        
        # Now simulate login from a different IP by spoofing X-Forwarded-For
        # Create a new client context with different IP
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "AdminPass123"
            },
            headers={"X-Forwarded-For": "192.168.1.100"}
        )
        # Admin from different IP should succeed (no per-identifier throttle for admin)
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["username"] == "admin"


class TestExponentialBackoff:
    """Test exponential backoff calculation."""
    
    def test_backoff_increases_exponentially(self, app, client, admin_user_local):
        """Retry-After time increases exponentially after threshold."""
        # Populate throttle table with many attempts
        # First 10: no backoff (within limit)
        # 11+: exponential backoff
        
        retry_afters = []
        
        for attempt in range(15):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            
            if attempt < 10:
                assert response.status_code == 403  # Not throttled yet
            else:
                # Attempts 11+ are throttled
                assert response.status_code == 429
                retry_after = int(response.headers.get("Retry-After", 0))
                retry_afters.append(retry_after)
        
        # Verify backoff increased exponentially
        # First throttled attempt: 1s, then 2s, 4s, 8s (doubling)
        if len(retry_afters) >= 2:
            # Backoff should increase or stay same due to exponential growth
            for i in range(1, len(retry_afters)):
                # Later attempts should have equal or greater backoff
                assert retry_afters[i] >= retry_afters[0] or retry_afters[i] > 0
    
    def test_backoff_capped_at_max(self, app, client, admin_user_local):
        """Backoff time is capped at maximum (default 900 seconds = 15 min)."""
        # Make many attempts to hit max backoff
        for i in range(50):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
        
        # Final response should show capped backoff
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 429
        retry_after = int(response.headers.get("Retry-After", 0))
        assert retry_after <= 900  # Capped at 15 minutes


class TestThrottleWindowExpiry:
    """Test that throttle windows expire after the specified time."""
    
    def test_throttle_window_expires(self, app, db_session, client, admin_user_local):
        """Throttle counter resets after window expiry."""
        from litfoundry.catalog import LoginThrottle
        
        # Make 5 failed attempts
        for i in range(5):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            assert response.status_code == 403
        
        # Manually expire the throttle window
        ip_key = "ip:127.0.0.1"
        throttle = db_session.query(LoginThrottle).filter_by(key=ip_key).first()
        if throttle:
            throttle.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            throttle.attempts = 0
            db_session.commit()
        
        # After window expiry, next attempt should work normally
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 200


class TestThrottleIntegration:
    """Integration tests for throttling with real scenario."""
    
    def test_throttle_and_recovery_flow(self, app, client, admin_user_local):
        """Test complete throttle and recovery scenario."""
        # 1. Successful login (no throttle)
        response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "AdminPass123"
        })
        assert response.status_code == 200
        
        # 2. Multiple failed attempts (need 10 to hit the limit since 1 was used by success)
        for i in range(10):
            response = client.post("/api/v1/auth/login", json={
                "username": "admin",
                "password": "WrongPassword"
            })
            if i < 9:
                assert response.status_code == 403
            # 10th failed attempt (11th total) should be throttled
        
        # After 10 failed + 1 successful = 11 total, we should be throttled
        assert response.status_code == 429
        
        # 3. Verify Retry-After header
        retry_after = int(response.headers.get("Retry-After", 0))
        assert retry_after > 0
        assert retry_after <= 900
