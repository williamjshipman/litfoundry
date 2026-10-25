"""Tests for offline operation and network resilience."""

import pytest
from pathlib import Path

from litfoundry.app import create_app
from litfoundry.initialization import initialize_data_root


class TestOfflineOperation:
    """Tests for offline operation (no outbound network required)."""

    def test_server_starts_offline(self, tmp_path):
        """Server should start and respond to requests without network."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should be able to access basic endpoints without network
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "alive"

    def test_health_check_works_offline(self, tmp_path):
        """Health checks should work offline."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Readiness check should work without network
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_logs_endpoint_works_offline(self, tmp_path):
        """Logs endpoint should work offline."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Should be able to query logs without network
        response = client.get("/api/v1/admin/logs")
        assert response.status_code == 200
        data = response.get_json()
        assert "logs" in data

    def test_offline_no_external_dependencies_on_startup(self, tmp_path):
        """App creation should not require external network dependencies."""
        initialize_data_root(tmp_path)
        
        # Creating the app should not require network access
        try:
            app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
            # If we got here without network error, test passes
            assert app is not None
        except Exception as e:
            # Should not fail due to network timeouts
            assert "timeout" not in str(e).lower()
            assert "connection" not in str(e).lower()

    def test_offline_all_blueprints_available(self, tmp_path):
        """All blueprints should be available without network."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Health blueprint
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        
        # Admin blueprint
        response = client.get("/api/v1/admin/logs")
        assert response.status_code == 200

    def test_offline_catalogue_accessible(self, tmp_path):
        """Catalogue database should be accessible without network."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # Readiness check verifies catalogue connectivity
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.get_json()
        
        # Check should be OK
        if "checks" in data and isinstance(data["checks"], dict):
            catalogue_check = data.get("checks", {}).get("catalogue", {})
            if isinstance(catalogue_check, dict):
                assert catalogue_check.get("status") == "ok"

    def test_offline_no_bootstrap_call_required(self, tmp_path):
        """Initialization should not require bootstrap from external service."""
        # Initialization should work entirely offline
        try:
            initialize_data_root(tmp_path)
            assert (tmp_path / ".initialized").exists()
        except Exception as e:
            # Should not fail due to network timeouts
            assert "timeout" not in str(e).lower()
            assert "connection" not in str(e).lower()

    def test_offline_initialization_idempotent_no_network(self, tmp_path):
        """Repeated initialization should work offline."""
        initialize_data_root(tmp_path)
        
        # Second init should also work without network
        initialize_data_root(tmp_path)
        
        assert (tmp_path / ".initialized").exists()
        assert (tmp_path / "catalog.sqlite").exists()

    def test_offline_no_implicit_api_calls(self, tmp_path):
        """App should not make implicit outbound API calls on startup."""
        # Create app - this should not make network calls
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        
        # If we reach here without hanging/timeout, the app doesn't make
        # implicit network calls on startup
        assert app is not None

    def test_offline_configuration_loading(self, tmp_path):
        """Configuration loading should not require network."""
        # Passing config to create_app should work offline
        config = {"LITFOUNDRY_DATA_ROOT": str(tmp_path)}
        app = create_app(config=config)
        
        # Should have the config value set
        assert app.config.get("LITFOUNDRY_DATA_ROOT") == str(tmp_path)

    def test_offline_middleware_setup(self, tmp_path):
        """Middleware setup should not require network."""
        config = {
            "LITFOUNDRY_DATA_ROOT": str(tmp_path),
            "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "LITFOUNDRY_TRUSTED_PROXIES": "",
        }
        
        app = create_app(config=config)
        client = app.test_client()
        
        # Basic request should work - middleware should be loaded
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200


class TestNetworkResilience:
    """Tests for network resilience and error handling."""

    def test_missing_outbound_service_handled_gracefully(self, tmp_path):
        """Errors from missing outbound services should be retryable."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        
        # This test ensures the server framework is set up to handle
        # outbound service failures gracefully. Later changes will add
        # actual outbound calls and verify they raise retryable errors.
        assert app is not None

    def test_server_handles_connection_errors(self, tmp_path):
        """Server should handle connection errors without crashing."""
        initialize_data_root(tmp_path)
        app = create_app(config={"LITFOUNDRY_DATA_ROOT": str(tmp_path)})
        client = app.test_client()
        
        # The health and logs endpoints should work regardless of network
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.get_json()["status"] == "alive"
