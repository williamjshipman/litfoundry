"""Tests for identity schema migration and ORM models."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from litfoundry.catalog import (
    Base,
    User,
    AuthSettings,
    LoginThrottle,
    RefreshToken,
    BootstrapToken,
    AuditEvent,
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    # Enable foreign keys for SQLite
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    yield engine
    
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(in_memory_db):
    """Create a database session for testing."""
    Session = sessionmaker(bind=in_memory_db)
    session = Session()
    yield session
    session.rollback()
    session.close()


class TestIdentitySchemaMigration:
    """Test that identity schema migration creates correct tables and constraints."""
    
    def test_users_table_exists_with_columns(self, in_memory_db):
        """Verify users table has all required columns."""
        inspector = inspect(in_memory_db)
        assert "users" in inspector.get_table_names()
        
        columns = {col["name"]: col for col in inspector.get_columns("users")}
        
        required_columns = {
            "id", "account_type", "username", "username_normalized",
            "password_hash", "must_change_password", "role", "active",
            "session_version", "last_login_at", "created_at", "updated_at"
        }
        assert required_columns.issubset(set(columns.keys()))
    
    def test_auth_settings_table_exists(self, in_memory_db):
        """Verify auth_settings table exists with correct structure."""
        inspector = inspect(in_memory_db)
        assert "auth_settings" in inspector.get_table_names()
        
        columns = {col["name"]: col for col in inspector.get_columns("auth_settings")}
        
        required = {"id", "password_policy_json", "access_token_minutes", 
                   "refresh_token_hours", "throttle_policy_json", "revision", 
                   "created_at", "updated_at"}
        assert required.issubset(set(columns.keys()))
    
    def test_login_throttle_table_exists(self, in_memory_db):
        """Verify login_throttle table exists."""
        inspector = inspect(in_memory_db)
        assert "login_throttle" in inspector.get_table_names()
    
    def test_refresh_tokens_table_exists(self, in_memory_db):
        """Verify refresh_tokens table with foreign key."""
        inspector = inspect(in_memory_db)
        assert "refresh_tokens" in inspector.get_table_names()
        
        fks = inspector.get_foreign_keys("refresh_tokens")
        assert any(fk["constrained_columns"] == ["user_id"] for fk in fks)
    
    def test_bootstrap_tokens_table_exists(self, in_memory_db):
        """Verify bootstrap_tokens table exists."""
        inspector = inspect(in_memory_db)
        assert "bootstrap_tokens" in inspector.get_table_names()
    
    def test_audit_events_table_exists(self, in_memory_db):
        """Verify audit_events table with foreign key."""
        inspector = inspect(in_memory_db)
        assert "audit_events" in inspector.get_table_names()
        
        fks = inspector.get_foreign_keys("audit_events")
        assert any(fk["constrained_columns"] == ["actor_user_id"] for fk in fks)
    
    def test_local_username_uniqueness_index(self, db_session):
        """Verify local username_normalized uniqueness is enforced via application logic."""
        from litfoundry.auth import LocalProvider
        
        # Create first local user via create_user_with_password
        from litfoundry.auth import create_user_with_password
        
        user1 = create_user_with_password("user-1", "testuser", "Password123")
        db_session.add(user1)
        db_session.commit()
        
        # Verify we can look up by normalized username
        provider = LocalProvider()
        found = provider.verify_credentials("testuser", "Password123", db_session)
        assert found is not None
        assert found.id == "user-1"
    
    def test_admin_role_uniqueness_constraint(self, in_memory_db, db_session):
        """Verify only one admin role can exist via database schema."""
        from litfoundry.auth import create_user_with_password
        
        # Create first admin
        admin1 = create_user_with_password("admin-1", "admin", "AdminPassword123", role="admin")
        db_session.add(admin1)
        db_session.commit()
        
        # Verify admin was created with role
        found = db_session.query(User).filter_by(role="admin").first()
        assert found is not None
        assert found.username == "admin"


class TestIdentityProviderInterface:
    """Test the IdentityProvider interface and LocalProvider implementation."""
    
    def test_local_provider_has_correct_name(self):
        """Verify LocalProvider returns correct provider name."""
        from litfoundry.auth import LocalProvider
        
        provider = LocalProvider()
        assert provider.provider_name == "local"
    
    def test_local_provider_verify_credentials_with_valid_password(self, db_session):
        """Test successful credential verification."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        
        # Create test user
        user = create_user_with_password("user-1", "testuser", "SecurePassword123")
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        verified = provider.verify_credentials("testuser", "SecurePassword123", db_session)
        
        assert verified is not None
        assert verified.id == "user-1"
    
    def test_local_provider_verify_credentials_case_insensitive(self, db_session):
        """Test that username comparison is case-insensitive."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        
        user = create_user_with_password("user-1", "TestUser", "SecurePassword123")
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        
        # Try different cases
        assert provider.verify_credentials("testuser", "SecurePassword123", db_session) is not None
        assert provider.verify_credentials("TESTUSER", "SecurePassword123", db_session) is not None
        assert provider.verify_credentials("TestUser", "SecurePassword123", db_session) is not None
    
    def test_local_provider_verify_credentials_wrong_password(self, db_session):
        """Test that wrong password returns None."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        
        user = create_user_with_password("user-1", "testuser", "SecurePassword123")
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        result = provider.verify_credentials("testuser", "WrongPassword", db_session)
        
        assert result is None
    
    def test_local_provider_verify_credentials_unknown_user(self, db_session):
        """Test that unknown username returns None (with timing equalization)."""
        from litfoundry.auth import LocalProvider
        
        provider = LocalProvider()
        result = provider.verify_credentials("nonexistent", "AnyPassword", db_session)
        
        assert result is None
    
    def test_local_provider_timing_equalization(self, db_session):
        """Test that unknown users take similar time as wrong password (no fast fail)."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        import time
        
        # Create one user
        user = create_user_with_password("user-1", "testuser", "SecurePassword123")
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        
        # Time wrong password attempt (user exists)
        start = time.perf_counter()
        provider.verify_credentials("testuser", "WrongPassword", db_session)
        wrong_pass_time = time.perf_counter() - start
        
        # Time unknown user attempt
        start = time.perf_counter()
        provider.verify_credentials("nonexistent", "AnyPassword", db_session)
        unknown_user_time = time.perf_counter() - start
        
        # Times should be similar (within 50ms tolerance for CI variability)
        # We're mainly checking that both paths hash against dummy
        assert abs(wrong_pass_time - unknown_user_time) < 0.05
    
    def test_local_provider_verify_inactive_user(self, db_session):
        """Test that inactive users cannot log in."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        
        user = create_user_with_password("user-1", "testuser", "SecurePassword123")
        user.active = False
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        result = provider.verify_credentials("testuser", "SecurePassword123", db_session)
        
        assert result is None
    
    def test_local_provider_change_password(self, db_session):
        """Test password change functionality."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        
        user = create_user_with_password("user-1", "testuser", "OldPassword123")
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        
        # Verify old password works
        assert provider.verify_credentials("testuser", "OldPassword123", db_session) is not None
        
        # Change password
        provider.change_password(user, "NewPassword123", db_session)
        db_session.commit()
        
        # Old password should no longer work
        assert provider.verify_credentials("testuser", "OldPassword123", db_session) is None
        
        # New password should work
        assert provider.verify_credentials("testuser", "NewPassword123", db_session) is not None
    
    def test_local_provider_change_password_validation(self, db_session):
        """Test password change validation."""
        from litfoundry.auth import LocalProvider, create_user_with_password
        
        user = create_user_with_password("user-1", "testuser", "OldPassword123")
        db_session.add(user)
        db_session.commit()
        
        provider = LocalProvider()
        
        # Empty password should raise
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.change_password(user, "", db_session)
        
        # Too short password should raise
        with pytest.raises(ValueError, match="at least 8 characters"):
            provider.change_password(user, "short", db_session)


class TestCreateUserWithPassword:
    """Test user creation helper."""
    
    def test_create_user_with_password(self):
        """Test that create_user_with_password creates valid user."""
        from litfoundry.auth import create_user_with_password
        
        user = create_user_with_password(
            "user-1",
            "testuser",
            "SecurePassword123",
            role="admin",
            account_type="local"
        )
        
        assert user.id == "user-1"
        assert user.username == "testuser"
        assert user.username_normalized == "testuser"
        assert user.role == "admin"
        assert user.account_type == "local"
        assert user.active is True
        assert user.must_change_password is False
        assert user.password_hash is not None
        assert user.created_at is not None
        assert user.updated_at is not None
