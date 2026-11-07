"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def app():
    """Create a Flask app for testing."""
    from litfoundry.app import create_app
    from litfoundry.initialization import initialize_data_root
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        initialize_data_root(root)
        
        config = {
            "LITFOUNDRY_DATA_ROOT": str(root),
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
            "SECRET_KEY": "test-secret-key-for-testing-only",
        }
        app = create_app(config)
        yield app


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture
def app_client(app):
    """Create a Flask app and test client."""
    return (app, app.test_client())


@pytest.fixture
def db_session(app):
    """Create a database session for testing."""
    from sqlalchemy.orm import scoped_session
    return app.config["DB_SESSION_FACTORY"]


@pytest.fixture
def admin_user_local(app, client, db_session):
    """Create an admin user and log them in."""
    from litfoundry.auth import get_password_hasher
    from litfoundry.catalog import User
    from datetime import datetime, timezone
    from uuid import uuid4
    
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
    db_session.refresh(admin)
    
    # Login to get JWT token automatically set in cookies
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "AdminPass123"
    })
    # If login fails, the tests will catch the error
    
    return admin

