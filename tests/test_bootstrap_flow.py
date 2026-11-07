"""Tests for bootstrap flow (setup gate, token generation, admin creation)."""

import pytest
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from flask.testing import FlaskClient
from sqlalchemy.orm import sessionmaker

from litfoundry.app import create_app
from litfoundry.catalog import (
    Base,
    User,
    BootstrapToken,
    create_catalog_engine,
)
from litfoundry.auth.bootstrap import (
    generate_bootstrap_token,
    hash_bootstrap_token,
    write_bootstrap_token_file,
    get_bootstrap_token_expiry_time,
    is_bootstrap_token_expired,
    delete_bootstrap_token_file,
)


@pytest.fixture
def temp_data_root(tmp_path):
    """Create a temporary data root for testing."""
    data_root = tmp_path / "test_data"
    data_root.mkdir()
    (data_root / "secret_material").mkdir()
    return data_root


@pytest.fixture
def test_db(temp_data_root):
    """Create a test database."""
    catalog_path = temp_data_root / "catalog.sqlite"
    engine = create_catalog_engine(catalog_path)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_app(test_db, temp_data_root):
    """Create Flask app configured for testing."""
    config = {
        "TESTING": True,
        "DATA_ROOT": temp_data_root,
        "LITFOUNDRY_DATA_ROOT": str(temp_data_root),
        "DB_SESSION_FACTORY": None,  # Will be set by app
        "SECRET_KEY": "test-secret-key",
    }
    app = create_app(config)
    
    # Override DB_SESSION_FACTORY to use our test DB
    Session = sessionmaker(bind=test_db)
    from sqlalchemy.orm import scoped_session
    app.config["DB_SESSION_FACTORY"] = scoped_session(Session)
    
    return app


@pytest.fixture
def client(test_app):
    """Flask test client."""
    return test_app.test_client()


class TestSetupGate:
    """Test the setup gate that blocks access while setup is pending."""
    
    def test_setup_status_no_admin(self, client):
        """GET /setup/status returns setup_required=true when no admin."""
        response = client.get("/api/v1/setup/status")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["setup_required"] is True
    
    def test_setup_status_with_admin(self, client, test_app):
        """GET /setup/status returns setup_required=false when admin exists."""
        db_session = test_app.config["DB_SESSION_FACTORY"]
        
        # Create admin user
        admin = User(
            id=str(uuid4()),
            account_type="local",
            username="admin",
            username_normalized="admin",
            password_hash="hash",
            role="admin",
            active=True,
            session_version=0,
            must_change_password=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(admin)
        db_session.commit()
        
        response = client.get("/api/v1/setup/status")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["setup_required"] is False


class TestBootstrapTokenGeneration:
    """Test bootstrap token generation and validation."""
    
    def test_generate_token(self):
        """Generate bootstrap token is base32 encoded."""
        token = generate_bootstrap_token()
        assert isinstance(token, str)
        assert len(token) > 0
        # Base32 encoded (without padding)
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in token)
    
    def test_hash_and_verify_token(self):
        """Token hash can be verified."""
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        
        assert isinstance(token_hash, str)
        assert token_hash.startswith("$argon2id$")
    
    def test_token_expiry_time(self):
        """Token expiry is 30 minutes from issue."""
        now = datetime.now(timezone.utc)
        expiry = get_bootstrap_token_expiry_time(now)
        
        # Should be about 30 minutes from now
        delta = expiry - now
        assert 29 * 60 < delta.total_seconds() < 31 * 60
    
    def test_token_expiry_check(self):
        """Expired token is detected."""
        now = datetime.now(timezone.utc)
        
        # Future time is not expired
        future = now + timedelta(minutes=10)
        assert not is_bootstrap_token_expired(future)
        
        # Past time is expired
        past = now - timedelta(seconds=1)
        assert is_bootstrap_token_expired(past)
    
    def test_write_token_file(self, temp_data_root):
        """Token file is written with restricted permissions."""
        token = generate_bootstrap_token()
        token_file = write_bootstrap_token_file(temp_data_root, token)
        
        assert token_file.exists()
        assert token_file.read_text().strip() == token
    
    def test_delete_token_file(self, temp_data_root):
        """Token file can be deleted."""
        token = generate_bootstrap_token()
        write_bootstrap_token_file(temp_data_root, token)
        
        assert (temp_data_root / "bootstrap-token.txt").exists()
        
        deleted = delete_bootstrap_token_file(temp_data_root)
        assert deleted is True
        assert not (temp_data_root / "bootstrap-token.txt").exists()


class TestAdminCreation:
    """Test admin account creation during setup."""
    
    def test_setup_admin_success(self, client, test_app):
        """POST /setup/admin creates admin with valid token and password."""
        db_session = test_app.config["DB_SESSION_FACTORY"]
        
        # Generate and store bootstrap token
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        now = datetime.now(timezone.utc)
        boot_token = BootstrapToken(
            token_hash=token_hash,
            expires_at=get_bootstrap_token_expiry_time(now),
            consumed_at=None,
        )
        db_session.add(boot_token)
        db_session.commit()
        
        # Setup admin
        response = client.post(
            "/api/v1/setup/admin",
            json={
                "token": token,
                "password": "AdminPassword123"
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        
        # Verify admin was created
        admin = db_session.query(User).filter_by(role="admin").first()
        assert admin is not None
        assert admin.username == "admin"
    
    def test_setup_admin_missing_token(self, client):
        """POST /setup/admin fails without token."""
        response = client.post(
            "/api/v1/setup/admin",
            json={
                "password": "AdminPassword123"
            }
        )
        
        assert response.status_code >= 400
    
    def test_setup_admin_weak_password(self, client, test_app):
        """POST /setup/admin fails with weak password."""
        db_session = test_app.config["DB_SESSION_FACTORY"]
        
        # Generate and store bootstrap token
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        now = datetime.now(timezone.utc)
        boot_token = BootstrapToken(
            token_hash=token_hash,
            expires_at=get_bootstrap_token_expiry_time(now),
            consumed_at=None,
        )
        db_session.add(boot_token)
        db_session.commit()
        
        # Try with weak password
        response = client.post(
            "/api/v1/setup/admin",
            json={
                "token": token,
                "password": "weak"
            }
        )
        
        assert response.status_code >= 400
        
        # Verify admin was NOT created
        admin = db_session.query(User).filter_by(role="admin").first()
        assert admin is None
    
    def test_setup_admin_invalid_token(self, client):
        """POST /setup/admin fails with invalid token."""
        response = client.post(
            "/api/v1/setup/admin",
            json={
                "token": "INVALID_TOKEN_XXXXXXXX",
                "password": "AdminPassword123"
            }
        )
        
        assert response.status_code >= 400
    
    def test_setup_admin_expired_token(self, client, test_app):
        """POST /setup/admin fails with expired token."""
        db_session = test_app.config["DB_SESSION_FACTORY"]
        
        # Create expired bootstrap token
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(minutes=1)
        
        boot_token = BootstrapToken(
            token_hash=token_hash,
            expires_at=expired_time,
            consumed_at=None,
        )
        db_session.add(boot_token)
        db_session.commit()
        
        response = client.post(
            "/api/v1/setup/admin",
            json={
                "token": token,
                "password": "AdminPassword123"
            }
        )
        
        assert response.status_code >= 400
    
    def test_setup_admin_already_exists(self, client, test_app):
        """POST /setup/admin fails if admin already exists."""
        db_session = test_app.config["DB_SESSION_FACTORY"]
        
        # Create existing admin
        admin = User(
            id=str(uuid4()),
            account_type="local",
            username="admin",
            username_normalized="admin",
            password_hash="hash",
            role="admin",
            active=True,
            session_version=0,
            must_change_password=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(admin)
        db_session.commit()
        
        # Try to create another admin
        response = client.post(
            "/api/v1/setup/admin",
            json={
                "token": "SOMETOKEN",
                "password": "AdminPassword123"
            }
        )
        
        assert response.status_code >= 400
    
    def test_setup_admin_token_consumed_once(self, client, test_app):
        """POST /setup/admin consumes token so it can't be reused."""
        db_session = test_app.config["DB_SESSION_FACTORY"]
        
        # Generate and store bootstrap token
        token = generate_bootstrap_token()
        token_hash = hash_bootstrap_token(token)
        now = datetime.now(timezone.utc)
        boot_token = BootstrapToken(
            token_hash=token_hash,
            expires_at=get_bootstrap_token_expiry_time(now),
            consumed_at=None,
        )
        db_session.add(boot_token)
        db_session.commit()
        
        # First setup succeeds
        response1 = client.post(
            "/api/v1/setup/admin",
            json={
                "token": token,
                "password": "AdminPassword123"
            }
        )
        assert response1.status_code == 200
        
        # Second setup with same token fails
        response2 = client.post(
            "/api/v1/setup/admin",
            json={
                "token": token,
                "password": "AdminPassword456"
            }
        )
        assert response2.status_code >= 400


class TestBootstrapTokenCommands:
    """Test CLI commands for bootstrap token."""
    
    def test_bootstrap_token_generation(self):
        """Bootstrap tokens are properly formatted."""
        token = generate_bootstrap_token()
        # Should be base32 without padding
        assert len(token) > 20
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in token)
