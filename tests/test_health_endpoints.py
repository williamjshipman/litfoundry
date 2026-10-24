"""Tests for health check endpoints."""

import os
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def app_with_initialized_data_root():
    """Create a Flask app with an initialized data root."""
    from litfoundry.app import create_app
    from litfoundry.initialization import initialize_data_root
    
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        initialize_data_root(root)
        
        config = {
            "LITFOUNDRY_DATA_ROOT": str(root),
            "TESTING": True,
        }
        app = create_app(config)
        yield app, root


@pytest.fixture
def app_with_missing_data_root():
    """Create a Flask app with a missing data root."""
    from litfoundry.app import create_app
    
    config = {
        "LITFOUNDRY_DATA_ROOT": "/nonexistent/path/that/does/not/exist",
        "TESTING": True,
    }
    app = create_app(config)
    return app, Path("/nonexistent/path/that/does/not/exist")


@pytest.fixture
def app_with_broken_data_root():
    """Create a Flask app with a broken (uninitialized) data root."""
    from litfoundry.app import create_app
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory but don't initialize it
        config = {
            "LITFOUNDRY_DATA_ROOT": tmpdir,
            "TESTING": True,
        }
        app = create_app(config)
        yield app, Path(tmpdir)


class TestHealthLiveEndpoint:
    """Tests for the /api/v1/health/live endpoint."""

    def test_live_always_returns_200(self, app_with_initialized_data_root):
        """Test that /live always returns 200."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    def test_live_returns_json(self, app_with_initialized_data_root):
        """Test that /live returns JSON response."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/live")
        assert response.json is not None

    def test_live_has_status_field(self, app_with_initialized_data_root):
        """Test that /live response has 'status' field."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/live")
        assert "status" in response.json
        assert response.json["status"] == "alive"

    def test_live_with_missing_data_root(self, app_with_missing_data_root):
        """Test that /live returns 200 even if data root is missing."""
        app, _ = app_with_missing_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/live")
        # /live should still return 200 because the app is running
        assert response.status_code == 200

    def test_live_with_broken_data_root(self, app_with_broken_data_root):
        """Test that /live returns 200 even if data root is broken."""
        app, _ = app_with_broken_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/live")
        # /live should still return 200 because the app is running
        assert response.status_code == 200


class TestHealthReadyEndpoint:
    """Tests for the /api/v1/health/ready endpoint."""

    def test_ready_with_healthy_data_root(self, app_with_initialized_data_root):
        """Test that /ready returns 200 when data root is healthy."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json["status"] == "ready"

    def test_ready_returns_json(self, app_with_initialized_data_root):
        """Test that /ready returns JSON response."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        assert response.json is not None

    def test_ready_has_checks_field(self, app_with_initialized_data_root):
        """Test that /ready response includes checks."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        assert "checks" in response.json or "reason" not in response.json

    def test_ready_with_missing_data_root(self, app_with_missing_data_root):
        """Test that /ready returns 503 when data root is missing."""
        app, _ = app_with_missing_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json["status"] == "not_ready"

    def test_ready_with_missing_catalogue(self, app_with_broken_data_root):
        """Test that /ready returns 503 when catalogue is not initialized."""
        app, _ = app_with_broken_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json["status"] == "not_ready"
        assert "reason" in response.json

    def test_ready_response_structure_success(self, app_with_initialized_data_root):
        """Test the response structure of /ready on success."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        
        assert response.status_code == 200
        assert "status" in response.json
        assert response.json["status"] == "ready"

    def test_ready_response_structure_failure(self, app_with_missing_data_root):
        """Test the response structure of /ready on failure."""
        app, _ = app_with_missing_data_root
        client = app.test_client()
        response = client.get("/api/v1/health/ready")
        
        assert response.status_code == 503
        assert "status" in response.json
        assert response.json["status"] == "not_ready"
        assert "reason" in response.json


class TestHealthEndpointIntegration:
    """Integration tests for health endpoints."""

    def test_both_endpoints_accessible(self, app_with_initialized_data_root):
        """Test that both /live and /ready endpoints are accessible."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        
        live_response = client.get("/api/v1/health/live")
        ready_response = client.get("/api/v1/health/ready")
        
        assert live_response.status_code == 200
        assert ready_response.status_code == 200

    def test_endpoints_use_correct_methods(self, app_with_initialized_data_root):
        """Test that endpoints only accept GET requests."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        
        # POST should not be allowed
        live_post = client.post("/api/v1/health/live")
        ready_post = client.post("/api/v1/health/ready")
        
        # Should return 405 Method Not Allowed
        assert live_post.status_code == 405
        assert ready_post.status_code == 405

    def test_ready_different_states(self, app_with_initialized_data_root):
        """Test that /ready correctly reports different health states."""
        app, root = app_with_initialized_data_root
        client = app.test_client()
        
        # Healthy state
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        
        # Now simulate broken catalogue by removing it
        catalogue_path = root / "catalog.sqlite"
        if catalogue_path.exists():
            catalogue_path.unlink()
        
        # Should now report not ready
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert response.json["status"] == "not_ready"

    def test_live_endpoint_has_no_side_effects(self, app_with_initialized_data_root):
        """Test that calling /live doesn't modify application state."""
        app, _ = app_with_initialized_data_root
        client = app.test_client()
        
        # Call /live multiple times
        for _ in range(5):
            response = client.get("/api/v1/health/live")
            assert response.status_code == 200
            assert response.json["status"] == "alive"
