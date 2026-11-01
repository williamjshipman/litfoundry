"""Tests for server configuration and health checks."""

import os
import tempfile

from litfoundry.app import create_app
from litfoundry.config import Config


class TestServerConfiguration:
    """Test that serve command properly configures the application."""

    def test_create_app_with_explicit_config(self):
        """Test that create_app() applies passed configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_RUN_MODE": "workstation",
                "LITFOUNDRY_PORT": 9999,
            }
            app = create_app(config)

            # Flask app should have the config values
            assert app.config.get("LITFOUNDRY_DATA_ROOT") == tmpdir
            assert app.config.get("LITFOUNDRY_RUN_MODE") == "workstation"
            assert app.config.get("LITFOUNDRY_PORT") == 9999

    def test_health_ready_without_initialization(self):
        """Test that health/ready returns 503 when data root is not configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_RUN_MODE": "workstation",
            }
            app = create_app(config)
            client = app.test_client()

            # Before initialization, ready should return 503
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "not_ready"

    def test_health_ready_with_config_missing_data_root(self):
        """Test that health/ready returns 503 when LITFOUNDRY_DATA_ROOT not in config."""
        config = {}  # No LITFOUNDRY_DATA_ROOT
        app = create_app(config)
        client = app.test_client()

        # Without data root in config, ready should return 503
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.get_json()
        assert "Data root not configured" in data["reason"]

    def test_health_live_always_returns_200(self):
        """Test that health/live always returns 200."""
        app = create_app()
        client = app.test_client()

        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "alive"

    def test_config_load_from_env_without_mode_has_no_default(self):
        """Test that Config.load_from_env() does NOT default mode to 'server'."""
        # Save current env
        old_mode = os.environ.get("LITFOUNDRY_RUN_MODE")

        try:
            # Remove env var
            if "LITFOUNDRY_RUN_MODE" in os.environ:
                del os.environ["LITFOUNDRY_RUN_MODE"]

            config = Config.load_from_env()
            # Should be None (no default)
            assert config.LITFOUNDRY_RUN_MODE is None
        finally:
            # Restore env
            if old_mode is not None:
                os.environ["LITFOUNDRY_RUN_MODE"] = old_mode

    def test_config_to_dict_includes_all_keys(self):
        """Test that Config.to_dict() includes all LITFOUNDRY_ config keys."""
        config = Config()
        config_dict = config.to_dict()

        # Should include all LITFOUNDRY_ attributes
        assert "LITFOUNDRY_DATA_ROOT" in config_dict
        assert "LITFOUNDRY_RUN_MODE" in config_dict
        assert "LITFOUNDRY_PORT" in config_dict
        assert "LITFOUNDRY_TRUSTED_PROXIES" in config_dict
        assert "LITFOUNDRY_ALLOWED_HOSTS" in config_dict
        assert "LITFOUNDRY_CORS_ORIGINS" in config_dict

    def test_config_to_dict_does_not_include_process_names(self):
        """Test that Config.to_dict() excludes _PROCESS_NAME constants."""
        config = Config()
        config_dict = config.to_dict()

        # Should NOT include process names
        assert "LITFOUNDRY_SERVER_PROCESS_NAME" not in config_dict
        assert "LITFOUNDRY_WORKER_PROCESS_NAME" not in config_dict
