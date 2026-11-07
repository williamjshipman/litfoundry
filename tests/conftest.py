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
