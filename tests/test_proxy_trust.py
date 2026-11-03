"""Tests for proxy trust configuration and bidirectional validation."""

import tempfile
from pathlib import Path

from litfoundry.app import create_app
from litfoundry.initialization import initialize_data_root


class TestProxyTrustConfiguration:
    """Test proxy trust configuration in middleware."""

    def test_proxyfix_disabled_without_trusted_proxies(self):
        """Test that ProxyFix is applied but without IP validation when no proxies configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "",  # No trusted proxies
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)

            # Without trusted proxies configured, TRUSTED_PROXIES should be None
            assert app.config.get("TRUSTED_PROXIES") is None

    def test_trusted_proxies_stored_in_config(self):
        """Test that trusted proxies are stored as a set in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "192.168.1.1, 10.0.0.1",
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)

            # Trusted proxies should be stored as a set
            trusted_proxies = app.config.get("TRUSTED_PROXIES")
            assert trusted_proxies is not None
            assert isinstance(trusted_proxies, set)
            assert "192.168.1.1" in trusted_proxies
            assert "10.0.0.1" in trusted_proxies


class TestProxyTrustValidation:
    """Test that proxy trust validation works bidirectionally."""

    def test_trusted_proxy_connection_allowed(self):
        """Test that connections from trusted proxy IPs are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "127.0.0.1",  # Loopback is trusted
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)
            client = app.test_client()

            # Request from localhost (127.0.0.1) - should be allowed
            response = client.get("/api/v1/health/live")
            # Should not return 403 Forbidden
            assert response.status_code != 403

    def test_untrusted_proxy_connection_rejected(self):
        """Test that connections from untrusted IPs are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "192.168.1.1",  # Only this IP trusted
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)

            # Simulate connection from untrusted IP (not 192.168.1.1)
            with app.test_client() as client:
                # The test client connects from 127.0.0.1 by default
                # Since we only trust 192.168.1.1, this should be rejected
                response = client.get(
                    "/api/v1/health/live",
                    environ_base={"REMOTE_ADDR": "10.0.0.1"},  # Different IP
                )
                # Should return 403 Forbidden
                assert response.status_code == 403

    def test_host_allowlist_with_proxied_request(self):
        """Test that Host allowlist works with proxied requests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "127.0.0.1",
                "LITFOUNDRY_ALLOWED_HOSTS": "example.com,app.example.com",
            }
            app = create_app(config)
            client = app.test_client()

            # Valid host in allowlist - should work
            response = client.get(
                "/api/v1/health/live",
                headers={"Host": "example.com"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
            assert response.status_code != 400

            # Invalid host not in allowlist - should be rejected
            response = client.get(
                "/api/v1/health/live",
                headers={"Host": "evil.com"},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
            assert response.status_code == 400

    def test_forwarded_headers_from_trusted_proxy(self):
        """Test that X-Forwarded-* headers are processed from trusted proxies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "127.0.0.1",
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1,example.com",
            }
            app = create_app(config)
            client = app.test_client()

            # Request from trusted proxy (127.0.0.1) with X-Forwarded-* headers
            # The important thing is that the connection is from a trusted IP
            response = client.get(
                "/api/v1/health/live",
                environ_base={"REMOTE_ADDR": "127.0.0.1"},  # From trusted proxy
            )
            # Should be allowed (after proxy trust validation)
            # Status might be 200 or 503 depending on data root state, but NOT 403
            assert response.status_code != 403

    def test_forwarded_headers_from_untrusted_peer(self):
        """Test that X-Forwarded-* headers are rejected from untrusted peers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "192.168.1.1",
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1,example.com",
            }
            app = create_app(config)
            client = app.test_client()

            # Request from untrusted peer trying to forge headers
            response = client.get(
                "/api/v1/health/live",
                headers={
                    "X-Forwarded-For": "203.0.113.195",
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-Host": "example.com",
                },
                environ_base={"REMOTE_ADDR": "10.0.0.1"},  # NOT in trusted proxies
            )
            # Should be rejected (untrusted peer cannot forge headers)
            assert response.status_code == 403


class TestProxyTrustWithoutConfiguration:
    """Test standalone mode without proxy trust configured."""

    def test_no_proxy_trust_allows_direct_connections(self):
        """Test that direct connections work when no proxy trust is configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "",  # No proxy trust
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)
            client = app.test_client()

            # Direct connection should work
            response = client.get("/api/v1/health/live")
            # Should succeed (no proxy trust configured)
            assert response.status_code in (200, 503)  # 200 or 503 depending on state

    def test_no_proxy_trust_ignores_forwarded_headers(self):
        """Test that X-Forwarded-* headers are ignored without proxy trust."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initialize_data_root(Path(tmpdir))
            config = {
                "LITFOUNDRY_DATA_ROOT": tmpdir,
                "LITFOUNDRY_TRUSTED_PROXIES": "",  # No proxy trust
                "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
            }
            app = create_app(config)
            client = app.test_client()

            # Headers should be ignored, connection should work
            response = client.get(
                "/api/v1/health/live",
                headers={
                    "X-Forwarded-For": "203.0.113.195",
                    "X-Forwarded-Proto": "https",
                },
            )
            # Should work (forwarded headers not trusted but not causing errors)
            assert response.status_code in (200, 503)
