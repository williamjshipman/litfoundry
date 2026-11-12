"""Tests for pagination and concurrency control."""

import json
import pytest

from litfoundry.api.pagination import (
    PaginationParams,
    parse_pagination_params,
    sign_cursor,
    verify_cursor,
    create_etag,
    extract_etag_revision,
    check_if_match,
    check_if_match_conflict,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)


def test_parse_pagination_default():
    """Test parsing pagination params with defaults."""
    params = parse_pagination_params({})
    assert params.limit == DEFAULT_PAGE_SIZE
    assert params.cursor is None


def test_parse_pagination_custom_limit():
    """Test parsing custom limit."""
    params = parse_pagination_params({"limit": "100"})
    assert params.limit == 100


def test_parse_pagination_limit_clamping():
    """Test that limit is clamped to maximum."""
    params = parse_pagination_params({"limit": str(MAX_PAGE_SIZE + 100)})
    assert params.limit == MAX_PAGE_SIZE


def test_parse_pagination_invalid_limit():
    """Test that invalid limit defaults to default size."""
    params = parse_pagination_params({"limit": "invalid"})
    assert params.limit == DEFAULT_PAGE_SIZE


def test_parse_pagination_cursor():
    """Test parsing cursor parameter."""
    params = parse_pagination_params({"cursor": "abc123"})
    assert params.cursor == "abc123"


def test_cursor_signing_and_verification(app):
    """Test cursor signing and verification."""
    with app.app_context():
        data = {"last_id": "123", "sort_key": "created_at"}
        cursor = sign_cursor(data)
        
        # Cursor should be non-empty
        assert cursor
        assert isinstance(cursor, str)
        
        # Verification should return the same data
        verified = verify_cursor(cursor)
        assert verified == data


def test_tampered_cursor_rejected(app):
    """Test that tampered cursors are rejected."""
    with app.app_context():
        data = {"last_id": "123", "sort_key": "created_at"}
        cursor = sign_cursor(data)
        
        # Tamper with cursor by changing a character
        tampered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")
        
        # Verification should fail
        verified = verify_cursor(tampered)
        assert verified is None


def test_invalid_cursor_rejected(app):
    """Test that invalid cursors return None."""
    with app.app_context():
        # Test various invalid formats
        assert verify_cursor("") is None
        assert verify_cursor("not-base64!!!") is None
        assert verify_cursor("dGVzdA==") is None  # Valid base64 but no signature


def test_etag_creation():
    """Test ETag creation."""
    etag = create_etag(42)
    assert etag == 'W/"42"'


def test_etag_revision_extraction():
    """Test extracting revision from ETag."""
    etag = create_etag(123)
    revision = extract_etag_revision(etag)
    assert revision == 123


def test_etag_revision_extraction_invalid():
    """Test extracting revision from invalid ETag."""
    assert extract_etag_revision("invalid") is None
    assert extract_etag_revision("123") is None
    assert extract_etag_revision('W/"invalid"') is None
    assert extract_etag_revision("") is None


def test_check_if_match_success(client):
    """Test If-Match check when it matches."""
    @client.application.route("/test-if-match", methods=["PUT"])
    def test_if_match():
        result = check_if_match(1)
        return {"match": result}
    
    response = client.put("/test-if-match", headers={"If-Match": 'W/"1"'})
    assert response.get_json()["match"] is True


def test_check_if_match_mismatch(client):
    """Test If-Match check when it doesn't match."""
    @client.application.route("/test-if-match-mismatch", methods=["PUT"])
    def test_if_match_mismatch():
        result = check_if_match(2)
        return {"match": result}
    
    response = client.put("/test-if-match-mismatch", headers={"If-Match": 'W/"1"'})
    assert response.get_json()["match"] is False


def test_check_if_match_missing(client):
    """Test If-Match check when header is missing."""
    @client.application.route("/test-if-match-missing", methods=["PUT"])
    def test_if_match_missing():
        result = check_if_match(1)
        return {"match": result}
    
    response = client.put("/test-if-match-missing")
    assert response.get_json()["match"] is False


def test_concurrent_update_conflict(client):
    """Test concurrent update detection with If-Match."""
    @client.application.route("/test-concurrent", methods=["PUT"])
    def test_concurrent():
        # Simulate: current revision is 2, but client has If-Match for revision 1
        conflict = check_if_match_conflict(1, 2)
        if conflict:
            return conflict, conflict["status"]
        return {"updated": True}
    
    # Client has revision 1, but current is 2
    response = client.put("/test-concurrent", headers={"If-Match": 'W/"1"'})
    assert response.status_code == 409
    data = response.get_json()
    assert data["code"] == "CONFLICT"
    assert data["details"]["current_etag"] == 'W/"2"'


def test_concurrent_update_success(client):
    """Test concurrent update when If-Match matches current revision."""
    @client.application.route("/test-concurrent-ok", methods=["PUT"])
    def test_concurrent_ok():
        conflict = check_if_match_conflict(1, 1)
        if conflict:
            return conflict, 409
        return {"updated": True}
    
    response = client.put("/test-concurrent-ok", headers={"If-Match": 'W/"1"'})
    assert response.status_code == 200
    assert response.get_json()["updated"] is True


def test_pagination_limit_bounds():
    """Test pagination limit boundaries."""
    # Test zero
    params = parse_pagination_params({"limit": "0"})
    assert params.limit == DEFAULT_PAGE_SIZE
    
    # Test negative
    params = parse_pagination_params({"limit": "-10"})
    assert params.limit == DEFAULT_PAGE_SIZE
    
    # Test max exactly
    params = parse_pagination_params({"limit": str(MAX_PAGE_SIZE)})
    assert params.limit == MAX_PAGE_SIZE
