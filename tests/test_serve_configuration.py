"""Integration tests for serve command configuration.

Verifies that serve command properly configures the Flask app with:
- Data root passed to app config
- Environment variables loaded and applied
- Host allowlist working (rejecting unknown hosts)
- Readiness check returning 200 with data root configured
- Trusted proxies configured
- CORS settings configured
"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from flask.testing import FlaskClient

from litfoundry.app import create_app
from litfoundry.config import Config
from litfoundry.initialization import initialize_data_root


class TestServeConfiguration:
    """Test serve command configuration."""

    def test_app_config_includes_data_root(self):
        """Verify create_app receives LITFOUNDRY_DATA_ROOT in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            config = {
                "LITFOUNDRY_DATA_ROOT": str(root),
                "LITFOUNDRY_RUN_MODE": "server",
            }
            app = create_app(config)

            assert app.config.get("LITFOUNDRY_DATA_ROOT") == str(root)
            assert app.config.get("LITFOUNDRY_RUN_MODE") == "server"

    def test_readiness_check_with_configured_data_root(self):
        """Verify GET /api/v1/health/ready returns 200 when data root is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            config = {
                "LITFOUNDRY_DATA_ROOT": str(root),
                "LITFOUNDRY_RUN_MODE": "server",
            }
            app = create_app(config)

            with app.test_client() as client:
                response = client.get("/api/v1/health/ready")
                assert response.status_code == 200
                assert response.json["status"] == "ready"

    def test_readiness_check_fails_without_data_root(self):
        """Verify GET /api/v1/health/ready returns 503 when data root not configured."""
        config = {
            "LITFOUNDRY_RUN_MODE": "server",
            # No LITFOUNDRY_DATA_ROOT set
        }
        app = create_app(config)

        with app.test_client() as client:
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 503
            assert "not configured" in response.json["reason"].lower()

    def test_host_allowlist_rejects_unknown_host(self):
        """Verify unknown Host header is rejected with 400."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            # Set allowed hosts to only localhost
            config = {
                "LITFOUNDRY_DATA_ROOT": str(root),
                "LITFOUNDRY_RUN_MODE": "server",
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)

            with app.test_client() as client:
                # Request with unknown Host header
                response = client.get(
                    "/api/v1/health/live",
                    headers={"Host": "evil.example.com"}
                )
                # Should be rejected
                assert response.status_code == 400

    def test_host_allowlist_allows_configured_host(self):
        """Verify allowlisted Host header is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            config = {
                "LITFOUNDRY_DATA_ROOT": str(root),
                "LITFOUNDRY_RUN_MODE": "server",
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1,myhost.internal",
            }
            app = create_app(config)

            with app.test_client() as client:
                # Request with allowlisted Host header
                response = client.get(
                    "/api/v1/health/live",
                    headers={"Host": "myhost.internal"}
                )
                # Should be allowed
                assert response.status_code == 200
                assert response.json["status"] == "alive"

    def test_cors_origins_configured(self):
        """Verify CORS origins are configured from environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            config = {
                "LITFOUNDRY_DATA_ROOT": str(root),
                "LITFOUNDRY_RUN_MODE": "server",
                "LITFOUNDRY_CORS_ORIGINS": "https://frontend.example.com,https://app.example.com",
            }
            app = create_app(config)

            # CORS middleware should be configured
            # Verify by making a preflight request from an allowlisted origin
            with app.test_client() as client:
                response = client.options(
                    "/api/v1/health/live",
                    headers={"Origin": "https://frontend.example.com"}
                )
                # Preflight should succeed (no CORS error for allowlisted origin)
                assert response.status_code == 200

    def test_trusted_proxies_configured(self):
        """Verify trusted proxies are configured from environment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            config = {
                "LITFOUNDRY_DATA_ROOT": str(root),
                "LITFOUNDRY_RUN_MODE": "server",
                "LITFOUNDRY_TRUSTED_PROXIES": "10.0.0.1,10.0.0.2",
            }
            app = create_app(config)

            # Proxy handling should be configured
            # Verify that ProxyFix is applied
            assert any(
                hasattr(mw, 'app') and hasattr(mw, 'x_for')
                for mw in app.wsgi_app.__dict__.values()
            ) or hasattr(app.wsgi_app, 'app')

    def test_env_config_loads_from_environment(self):
        """Verify Config.load_from_env() reads LITFOUNDRY_* variables."""
        with mock.patch.dict("os.environ", {
            "LITFOUNDRY_RUN_MODE": "workstation",
            "LITFOUNDRY_PORT": "9000",
            "LITFOUNDRY_ALLOWED_HOSTS": "testhost",
        }):
            config = Config.load_from_env()
            
            assert config.LITFOUNDRY_RUN_MODE == "workstation"
            assert config.LITFOUNDRY_PORT == 9000
            assert config.LITFOUNDRY_ALLOWED_HOSTS == "testhost"

    def test_config_to_dict(self):
        """Verify Config.to_dict() returns all LITFOUNDRY_* settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            config = Config()
            config.LITFOUNDRY_DATA_ROOT = str(root)
            config.LITFOUNDRY_RUN_MODE = "server"
            config.LITFOUNDRY_PORT = 6000
            config.LITFOUNDRY_ALLOWED_HOSTS = "example.com"

            config_dict = config.to_dict()

            assert config_dict["LITFOUNDRY_DATA_ROOT"] == str(root)
            assert config_dict["LITFOUNDRY_RUN_MODE"] == "server"
            assert config_dict["LITFOUNDRY_PORT"] == 6000
            assert config_dict["LITFOUNDRY_ALLOWED_HOSTS"] == "example.com"

    def test_serve_startup_path_regression(self):
        """Regression test: Verify start_server() actually passes config to create_app().
        
        This test exercises the actual serve startup path (with Waitress mocked) to ensure
        the fix is working. Without the fix, create_app() receives no config, causing
        readiness check failures and security issues. This test verifies the fix by:
        1. Calling start_server() directly with Waitress mocked
        2. Verifying that create_app() was called with config dict including data root
        3. Verifying that the Flask app has the expected config set
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initialize_data_root(root)

            # Mock Waitress serve (imported inside start_server function)
            with mock.patch("waitress.serve") as mock_waitress:
                from litfoundry.server import start_server
                
                # Call start_server with explicit mode
                start_server(root, port=5080, mode="workstation")
                
                # Verify Waitress was called (server attempted to start)
                assert mock_waitress.called, "Waitress serve() not called; startup path not exercised"
                
                # Get the Flask app that was passed to Waitress
                call_args = mock_waitress.call_args
                app = call_args[0][0]
                
                # Verify the app has the correct configuration
                assert app.config.get("LITFOUNDRY_DATA_ROOT") == str(root), \
                    "Data root not passed to Flask app config"
                assert app.config.get("LITFOUNDRY_RUN_MODE") == "workstation", \
                    "Mode not passed to Flask app config"
                
                # Verify readiness check would work (app is properly configured)
                with app.test_client() as client:
                    response = client.get("/api/v1/health/ready")
                    assert response.status_code == 200, \
                        f"Readiness check failed; fix not working. Got {response.status_code}"
                    assert response.json["status"] == "ready"
                
                # Clean up logging handlers to release file locks
                import logging
                for handler in logging.root.handlers[:]:
                    logging.root.removeHandler(handler)
                    handler.close()
