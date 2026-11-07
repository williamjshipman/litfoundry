"""Tests for security headers and origin validation."""

import pytest
from urllib.parse import urlencode


def test_csp_header_present(client):
    """Test that CSP header is present in responses."""
    response = client.get("/")
    
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "unsafe-eval" not in csp
    assert "unsafe-inline" not in csp


def test_x_content_type_options_header(client):
    """Test that X-Content-Type-Options header prevents MIME sniffing."""
    response = client.get("/")
    
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_x_frame_options_header(client):
    """Test that X-Frame-Options prevents clickjacking."""
    response = client.get("/")
    
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"


def test_authenticated_response_not_cached(client):
    """Test that authenticated API responses are marked non-cacheable."""
    @client.application.route("/test-auth-cache")
    def test_auth():
        # Simulate authenticated request
        from flask import request
        request.user = "test_user"
        return {"status": "ok"}
    
    response = client.get("/test-auth-cache")
    
    assert "Cache-Control" in response.headers
    cache_control = response.headers["Cache-Control"]
    assert "no-store" in cache_control or "no-cache" in cache_control


def test_cross_site_post_rejected(client):
    """Test that POST from different origin returns 403."""
    @client.application.route("/test-csrf", methods=["POST"])
    def test_csrf():
        return {"updated": True}
    
    # POST with cross-origin
    response = client.post(
        "/test-csrf",
        headers={"Origin": "https://evil.example"},
    )
    
    assert response.status_code == 403
    data = response.get_json()
    assert data["code"] == "FORBIDDEN"


def test_same_origin_post_allowed(client, app):
    """Test that POST from same origin is allowed."""
    @client.application.route("/test-same-origin", methods=["POST"])
    def test_same_origin():
        return {"updated": True}
    
    # Make request (test client uses localhost by default)
    response = client.post(
        "/test-same-origin",
        headers={"Origin": "http://localhost"},
    )
    
    # Should not be rejected by origin check (may fail for other reasons)
    assert response.status_code != 403


def test_cross_origin_allowlist(client, app):
    """Test that allowlisted origins are permitted."""
    app.config["LITFOUNDRY_CORS_ORIGINS"] = "https://trusted.example"
    
    @client.application.route("/test-allowlist", methods=["POST"])
    def test_allowlist():
        return {"updated": True}
    
    response = client.post(
        "/test-allowlist",
        headers={"Origin": "https://trusted.example"},
    )
    
    # Should not be rejected
    assert response.status_code != 403


def test_safe_redirect_relative_path():
    """Test that safe_redirect accepts relative paths."""
    from litfoundry.api.security import safe_redirect
    
    result = safe_redirect("/dashboard")
    assert result == "/dashboard"
    
    result = safe_redirect("/projects/123/edit")
    assert result == "/projects/123/edit"


def test_safe_redirect_rejects_absolute_urls():
    """Test that safe_redirect rejects absolute URLs."""
    from litfoundry.api.security import safe_redirect
    
    result = safe_redirect("https://evil.example/")
    assert result == "/"
    
    result = safe_redirect("http://attacker.com")
    assert result == "/"


def test_safe_redirect_uses_default():
    """Test that safe_redirect uses default for invalid paths."""
    from litfoundry.api.security import safe_redirect
    
    result = safe_redirect(None)
    assert result == "/"
    
    result = safe_redirect("")
    assert result == "/"
    
    result = safe_redirect("javascript:alert(1)")
    assert result == "/"


def test_query_string_tokens_ignored(client):
    """Test that tokens in query strings are ignored."""
    @client.application.route("/test-query-token")
    def test_query_token():
        return {"ok": True}
    
    # Request with token in query string
    response = client.get("/test-query-token?access_token=secret123")
    
    # Should succeed (token is ignored, no auth provided)
    assert response.status_code == 200


def test_referer_origin_fallback(client):
    """Test that Referer header is used when Origin is missing."""
    @client.application.route("/test-referer", methods=["POST"])
    def test_referer():
        return {"ok": True}
    
    # POST with Referer but no Origin (older browsers)
    response = client.post(
        "/test-referer",
        headers={"Referer": "https://evil.example/attack"},
    )
    
    # Should be rejected
    assert response.status_code == 403


def test_missing_origin_unsafe_method_rejected(client):
    """Test that unsafe methods without Origin header are rejected."""
    @client.application.route("/test-no-origin", methods=["POST"])
    def test_no_origin():
        return {"ok": True}
    
    # POST with neither Origin nor Referer
    response = client.post("/test-no-origin")
    
    # Should be rejected
    assert response.status_code == 403
    data = response.get_json()
    assert data["code"] == "FORBIDDEN"


def test_get_requests_not_origin_checked(client):
    """Test that GET requests are not subject to origin checks."""
    @client.application.route("/test-get-safe")
    def test_get_safe():
        return {"ok": True}
    
    response = client.get("/test-get-safe")
    
    # GET without Origin should succeed (no origin check on safe methods)
    assert response.status_code == 200


def test_safe_methods_no_origin_required(client):
    """Test that safe methods don't require Origin header."""
    @client.application.route("/test-safe-methods")
    def test_safe():
        return {"ok": True}
    
    # GET without Origin should succeed
    response = client.get("/test-safe-methods", headers={})
    assert response.status_code == 200
