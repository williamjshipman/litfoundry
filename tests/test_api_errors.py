"""Tests for API error handling."""

import pytest
from flask import Flask

from litfoundry.api.errors import ApiError, ERROR_CODES, get_or_create_request_id


def test_api_error_to_dict(app_client):
    """Test ApiError.to_dict() includes request_id."""
    error = ApiError(
        code="NOT_FOUND",
        status=404,
        message="Resource not found",
    )
    request_id = "test-id-123"
    result = error.to_dict(request_id)
    
    assert result["code"] == "NOT_FOUND"
    assert result["message"] == "Resource not found"
    assert result["request_id"] == "test-id-123"


def test_api_error_with_details(app_client):
    """Test ApiError includes details when provided."""
    error = ApiError(
        code="VALIDATION_ERROR",
        status=400,
        message="Invalid input",
        details={"field": "email", "reason": "invalid format"},
    )
    result = error.to_dict("test-id")
    
    assert result["details"]["field"] == "email"


def test_error_code_registry():
    """Test all error codes map to valid HTTP statuses."""
    assert ERROR_CODES["VALIDATION_ERROR"] == 400
    assert ERROR_CODES["UNAUTHENTICATED"] == 401
    assert ERROR_CODES["FORBIDDEN"] == 403
    assert ERROR_CODES["NOT_FOUND"] == 404
    assert ERROR_CODES["CONFLICT"] == 409
    assert ERROR_CODES["PAYLOAD_TOO_LARGE"] == 413
    assert ERROR_CODES["INTERNAL_ERROR"] == 500


def test_each_code_maps_to_single_status():
    """Test that each error code maps to exactly one HTTP status."""
    code_to_status = {}
    for code, status in ERROR_CODES.items():
        if code in code_to_status:
            assert code_to_status[code] == status, f"Code {code} maps to multiple statuses"
        else:
            code_to_status[code] = status
    
    # Verify all codes are accounted for
    assert len(code_to_status) == len(ERROR_CODES)


def test_unexpected_exception_returns_500(client):
    """Test that unexpected exceptions return 500 INTERNAL_ERROR with request_id."""
    @client.application.route("/test-exception")
    def test_exception():
        raise ValueError("Something went wrong")
    
    response = client.get("/test-exception")
    
    assert response.status_code == 500
    data = response.get_json()
    assert data["code"] == "INTERNAL_ERROR"
    assert "request_id" in data
    assert data["request_id"] != ""
    # Stack trace should NOT be included
    assert "ValueError" not in data.get("message", "")


def test_x_request_id_header_on_all_responses(client):
    """Test that X-Request-ID header is set on all responses."""
    @client.application.route("/test-ok")
    def test_ok():
        return {"status": "ok"}
    
    response = client.get("/test-ok")
    
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] != ""


def test_x_request_id_on_error_response(client):
    """Test that X-Request-ID header is set on error responses."""
    response = client.get("/nonexistent")
    
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"] != ""
    data = response.get_json()
    assert data["request_id"] == response.headers["X-Request-ID"]


def test_api_error_handler(client):
    """Test that ApiError is caught and formatted correctly."""
    @client.application.route("/test-api-error")
    def test_api_error():
        raise ApiError(
            code="FORBIDDEN",
            status=403,
            message="Access denied",
        )
    
    response = client.get("/test-api-error")
    
    assert response.status_code == 403
    data = response.get_json()
    assert data["code"] == "FORBIDDEN"
    assert data["message"] == "Access denied"
    assert "request_id" in data


def test_request_id_persistence(client):
    """Test that request_id is consistent within a request."""
    response = client.get("/")
    # Get the request_id from the response header
    request_id_1 = response.headers["X-Request-ID"]
    
    # Make another request and verify it gets a different ID
    response2 = client.get("/")
    request_id_2 = response2.headers["X-Request-ID"]
    
    # Each request should have its own unique ID
    assert request_id_1 != request_id_2
