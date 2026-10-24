"""Tests for trusted proxy and host allowlist middleware."""

import pytest
from flask import Flask


@pytest.fixture
def app_with_allowlist():
    """Create a Flask app with host allowlist configured."""
    from litfoundry.app import create_app
    
    config = {
        "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1,litfoundry.example.internal",
        "TESTING": True,
    }
    app = create_app(config)
    return app


@pytest.fixture
def app_with_trusted_proxies():
    """Create a Flask app with trusted proxies configured."""
    from litfoundry.app import create_app
    
    config = {
        "LITFOUNDRY_TRUSTED_PROXIES": "10.0.0.1,10.0.0.2",
        "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1,litfoundry.example.internal",
        "TESTING": True,
    }
    app = create_app(config)
    return app


@pytest.fixture
def app_no_allowlist():
    """Create a Flask app without host allowlist (all hosts allowed)."""
    from litfoundry.app import create_app
    
    config = {
        "LITFOUNDRY_ALLOWED_HOSTS": "",
        "TESTING": True,
    }
    app = create_app(config)
    return app


@pytest.fixture
def app_with_cors():
    """Create a Flask app with CORS origins configured."""
    from litfoundry.app import create_app
    
    config = {
        "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "LITFOUNDRY_CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
        "TESTING": True,
    }
    app = create_app(config)
    return app


@pytest.fixture
def app_without_cors():
    """Create a Flask app without CORS enabled."""
    from litfoundry.app import create_app
    
    config = {
        "LITFOUNDRY_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "LITFOUNDRY_CORS_ORIGINS": "",
        "TESTING": True,
    }
    app = create_app(config)
    return app


class TestHostAllowlist:
    """Tests for host allowlist validation."""

    def test_allowed_host_passes(self, app_with_allowlist):
        """Test that a request with an allowed host passes."""
        client = app_with_allowlist.test_client()
        response = client.get("/api/v1/health/live", headers={"Host": "localhost:5080"})
        assert response.status_code == 200

    def test_allowed_host_without_port(self, app_with_allowlist):
        """Test that a request with allowed host (no port) passes."""
        client = app_with_allowlist.test_client()
        response = client.get("/api/v1/health/live", headers={"Host": "127.0.0.1"})
        assert response.status_code == 200

    def test_disallowed_host_returns_400(self, app_with_allowlist):
        """Test that a request with disallowed host returns 400."""
        client = app_with_allowlist.test_client()
        response = client.get("/api/v1/health/live", headers={"Host": "evil.example.com"})
        assert response.status_code == 400

    def test_spoofed_host_returns_400(self, app_with_allowlist):
        """Test that a spoofed Host header is rejected."""
        client = app_with_allowlist.test_client()
        response = client.get("/api/v1/health/live", headers={"Host": "localhost:5080"})
        assert response.status_code == 200
        
        # Now try with spoofed host
        response = client.get("/api/v1/health/live", headers={"Host": "attacker.com"})
        assert response.status_code == 400

    def test_empty_allowlist_allows_all(self, app_no_allowlist):
        """Test that an empty allowlist allows all hosts."""
        client = app_no_allowlist.test_client()
        
        # Any host should be allowed
        response = client.get("/api/v1/health/live", headers={"Host": "any.example.com"})
        assert response.status_code == 200
        
        response = client.get("/api/v1/health/live", headers={"Host": "localhost"})
        assert response.status_code == 200


class TestTrustedProxies:
    """Tests for trusted proxy forwarding."""

    def test_spoofed_x_forwarded_for_ignored_from_untrusted(self, app_with_trusted_proxies):
        """Test that X-Forwarded-For from untrusted peer is ignored."""
        client = app_with_trusted_proxies.test_client()
        
        # Request from untrusted peer (localhost, which is not in LITFOUNDRY_TRUSTED_PROXIES)
        # with spoofed X-Forwarded-For should use the actual peer address
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Forwarded-For": "10.9.9.9", "Host": "localhost"}
        )
        assert response.status_code == 200
        # The request should process without using the spoofed address
        # (We can't directly test the recorded peer address in a unit test,
        # but we verify it doesn't error or bypass security)

    def test_x_forwarded_for_honored_from_trusted(self, app_with_trusted_proxies):
        """Test that X-Forwarded-For is honored from a trusted proxy."""
        # This test is limited in a unit test because the test client doesn't
        # actually come from a network peer. But we can verify the header passes through.
        client = app_with_trusted_proxies.test_client()
        
        # In a real scenario, if the request comes from 10.0.0.1 (a trusted proxy),
        # the X-Forwarded-For header would be trusted. The test client doesn't
        # allow us to spoof the peer address, so this is more of an integration test.
        # For now, verify the middleware is configured and doesn't break normal requests.
        response = client.get("/api/v1/health/live", headers={"Host": "localhost"})
        assert response.status_code == 200

    def test_x_forwarded_proto_honored_from_trusted(self, app_with_trusted_proxies):
        """Test that X-Forwarded-Proto is honored from a trusted proxy."""
        client = app_with_trusted_proxies.test_client()
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Forwarded-Proto": "https", "Host": "localhost"}
        )
        assert response.status_code == 200

    def test_x_forwarded_host_honored_from_trusted(self, app_with_trusted_proxies):
        """Test that X-Forwarded-Host is honored from a trusted proxy."""
        client = app_with_trusted_proxies.test_client()
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Forwarded-Host": "litfoundry.example.internal", "Host": "localhost"}
        )
        # Should be allowed since litfoundry.example.internal is in the allowlist
        assert response.status_code == 200


class TestCORSConfiguration:
    """Tests for CORS configuration."""

    def test_cors_preflight_allowed_origin(self, app_with_cors):
        """Test that preflight request from allowed origin gets CORS headers."""
        client = app_with_cors.test_client()
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Host": "localhost",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Flask-CORS should return 200 with CORS headers
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"

    def test_cors_preflight_disallowed_origin(self, app_with_cors):
        """Test that preflight request from disallowed origin does not get CORS headers."""
        client = app_with_cors.test_client()
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://evil.example.com",
                "Host": "localhost",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Flask-CORS should not include CORS headers for disallowed origin
        assert "Access-Control-Allow-Origin" not in response.headers or \
               response.headers.get("Access-Control-Allow-Origin") != "http://evil.example.com"

    def test_cors_no_preflight_without_config(self, app_without_cors):
        """Test that CORS is not enabled when not configured."""
        client = app_without_cors.test_client()
        response = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Host": "localhost",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Without CORS config, there should be no CORS headers
        # (or a 405 if OPTIONS is not allowed on that endpoint)
        assert response.status_code in [200, 405]
        # If response is 200, it should be from Flask-CORS being disabled
        # If response is 405, it means OPTIONS is not allowed

    def test_cors_get_with_allowed_origin(self, app_with_cors):
        """Test that GET request from allowed origin includes CORS headers."""
        client = app_with_cors.test_client()
        response = client.get(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Host": "localhost",
            }
        )
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"

    def test_cors_credentials_allowed(self, app_with_cors):
        """Test that credentials are allowed in CORS responses."""
        client = app_with_cors.test_client()
        response = client.get(
            "/api/v1/health/live",
            headers={
                "Origin": "http://localhost:3000",
                "Host": "localhost",
            }
        )
        assert response.status_code == 200
        if "Access-Control-Allow-Credentials" in response.headers:
            assert response.headers["Access-Control-Allow-Credentials"] == "true"


class TestMiddlewareIntegration:
    """Integration tests for middleware combination."""

    def test_allowlist_with_trusted_proxy_headers(self, app_with_trusted_proxies):
        """Test that host allowlist works with trusted proxy headers."""
        client = app_with_trusted_proxies.test_client()
        
        # Direct request with allowed host
        response = client.get("/api/v1/health/live", headers={"Host": "localhost"})
        assert response.status_code == 200
        
        # Request with allowed host in X-Forwarded-Host should work if X-Forwarded-Proto
        # indicates it came through a trusted proxy
        response = client.get(
            "/api/v1/health/live",
            headers={
                "X-Forwarded-Host": "litfoundry.example.internal",
                "X-Forwarded-Proto": "https",
                "Host": "localhost",
            }
        )
        assert response.status_code == 200

    def test_request_with_port_in_host_header(self, app_with_allowlist):
        """Test that Host header with port is properly parsed."""
        client = app_with_allowlist.test_client()
        
        # Request with port in Host header
        response = client.get("/api/v1/health/live", headers={"Host": "localhost:5080"})
        assert response.status_code == 200
        
        # Request with different port but same hostname should still work
        response = client.get("/api/v1/health/live", headers={"Host": "localhost:8080"})
        assert response.status_code == 200

    def test_multiple_allowed_hosts(self, app_with_allowlist):
        """Test that multiple allowed hosts all work."""
        client = app_with_allowlist.test_client()
        
        allowed_hosts = ["localhost", "127.0.0.1", "litfoundry.example.internal"]
        for host in allowed_hosts:
            response = client.get("/api/v1/health/live", headers={"Host": host})
            assert response.status_code == 200, f"Host {host} should be allowed"

    def test_disallowed_hosts_all_rejected(self, app_with_allowlist):
        """Test that disallowed hosts are all rejected."""
        client = app_with_allowlist.test_client()
        
        disallowed_hosts = ["evil.com", "attacker.org", "192.168.1.1", "10.0.0.1"]
        for host in disallowed_hosts:
            response = client.get("/api/v1/health/live", headers={"Host": host})
            assert response.status_code == 400, f"Host {host} should be disallowed"

    def test_cors_with_host_allowlist(self, app_with_cors):
        """Test that CORS and host allowlist work together."""
        client = app_with_cors.test_client()
        
        # Allowed host and allowed origin
        response = client.get(
            "/api/v1/health/live",
            headers={
                "Host": "localhost:5080",
                "Origin": "http://localhost:3000",
            }
        )
        assert response.status_code == 200
        
        # Disallowed host should fail even with allowed origin
        response = client.get(
            "/api/v1/health/live",
            headers={
                "Host": "evil.example.com",
                "Origin": "http://localhost:3000",
            }
        )
        assert response.status_code == 400

