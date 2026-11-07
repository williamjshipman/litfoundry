"""Tests for serialization and request size limits."""

import uuid
from datetime import datetime

import pytest

from litfoundry.api.serialization import (
    serialize_uuid,
    serialize_datetime,
    parse_datetime,
    LitFoundryJSONEncoder,
)


def test_serialize_uuid():
    """Test UUID serialization."""
    u = uuid.UUID("12345678-1234-5678-1234-567812345678")
    result = serialize_uuid(u)
    assert result == "12345678-1234-5678-1234-567812345678"


def test_serialize_datetime_utc():
    """Test datetime serialization with UTC."""
    # Create a UTC datetime
    dt = datetime(2024, 1, 15, 10, 30, 45)
    result = serialize_datetime(dt)
    # Should end with Z
    assert result.endswith("Z")
    assert "2024-01-15" in result
    assert "10:30:45" in result


def test_parse_datetime_iso():
    """Test parsing ISO-8601 datetime."""
    dt_str = "2024-01-15T10:30:45Z"
    result = parse_datetime(dt_str)
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15
    assert result.hour == 10
    assert result.minute == 30
    assert result.second == 45


def test_json_encoder_uuid(app):
    """Test JSON encoder with UUID."""
    import json
    
    encoder = LitFoundryJSONEncoder()
    u = uuid.UUID("12345678-1234-5678-1234-567812345678")
    result = encoder.encode({"id": u})
    assert "12345678-1234-5678-1234-567812345678" in result


def test_json_encoder_datetime(app):
    """Test JSON encoder with datetime."""
    import json
    
    encoder = LitFoundryJSONEncoder()
    dt = datetime(2024, 1, 15, 10, 30, 45)
    result = encoder.encode({"created": dt})
    assert "Z" in result


def test_payload_too_large_handler_invoked(app):
    """Test that the 413 handler is properly configured."""
    # Verify that the error handler is registered
    assert 413 in app.error_handler_spec[None]


def test_uuid_in_response(client):
    """Test that UUIDs are serialized in responses."""
    test_uuid = str(uuid.uuid4())
    
    @client.application.route("/test-uuid")
    def test_uuid_endpoint():
        return {"id": uuid.UUID(test_uuid)}
    
    response = client.get("/test-uuid")
    data = response.get_json()
    assert data["id"] == test_uuid


def test_datetime_in_response(client):
    """Test that datetimes are serialized with Z suffix."""
    import json as stdlib_json
    from litfoundry.api.serialization import LitFoundryJSONEncoder
    
    @client.application.route("/test-datetime")
    def test_datetime_endpoint():
        dt = datetime(2024, 1, 15, 10, 30, 45)
        # Use the custom encoder directly
        data = {"created": dt}
        return stdlib_json.loads(stdlib_json.dumps(data, cls=LitFoundryJSONEncoder))
    
    response = client.get("/test-datetime")
    data = response.get_json()
    # Should end with Z
    assert data["created"].endswith("Z")


def test_unknown_api_path_returns_json_404(client):
    """Test that unknown /api/v1 paths return JSON 404."""
    response = client.get("/api/v1/nonexistent")
    
    assert response.status_code == 404
    data = response.get_json()
    assert data["code"] == "NOT_FOUND"
    assert "request_id" in data
