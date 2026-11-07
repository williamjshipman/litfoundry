"""Pagination and concurrency control helpers for the API."""

import hmac
import hashlib
import json
import base64
from typing import Any, Optional, TypeVar
from dataclasses import dataclass

from flask import current_app, request


T = TypeVar("T")


# Default pagination limits
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


@dataclass
class PaginationParams:
    """Pagination parameters parsed from request."""

    limit: int
    cursor: Optional[str] = None


@dataclass
class PaginatedResponse:
    """Response data for paginated collections."""

    items: list[Any]
    limit: int
    cursor: Optional[str] = None


def parse_pagination_params(query_args: dict) -> PaginationParams:
    """Parse pagination parameters from query string."""
    try:
        limit = int(query_args.get("limit", DEFAULT_PAGE_SIZE))
    except (ValueError, TypeError):
        limit = DEFAULT_PAGE_SIZE

    # Clamp to maximum
    if limit > MAX_PAGE_SIZE:
        limit = MAX_PAGE_SIZE
    if limit < 1:
        limit = DEFAULT_PAGE_SIZE

    cursor = query_args.get("cursor")

    return PaginationParams(limit=limit, cursor=cursor)


def sign_cursor(data: dict) -> str:
    """Sign and encode a cursor object."""
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)
    # Use app secret key for signing
    secret = current_app.config.get("SECRET_KEY")
    if not secret:
        raise ValueError("SECRET_KEY not configured")
    
    # Ensure secret is bytes
    if isinstance(secret, str):
        secret = secret.encode()

    signature = hmac.new(secret, payload.encode(), hashlib.sha256).digest()
    # Combine payload and signature, then base64 encode
    combined = payload.encode() + b"|" + signature
    return base64.urlsafe_b64encode(combined).decode().rstrip("=")


def verify_cursor(cursor: str) -> Optional[dict]:
    """Verify and decode a cursor, return None if tampered."""
    try:
        # Add back padding if needed
        padding = 4 - (len(cursor) % 4)
        if padding != 4:
            cursor = cursor + ("=" * padding)

        combined = base64.urlsafe_b64decode(cursor)
        parts = combined.rsplit(b"|", 1)
        if len(parts) != 2:
            return None

        payload, signature = parts
        secret = current_app.config.get("SECRET_KEY")
        if not secret:
            return None

        # Ensure secret is bytes
        if isinstance(secret, str):
            secret = secret.encode()

        expected_sig = hmac.new(secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        return json.loads(payload)
    except Exception:
        return None


def create_etag(revision: int) -> str:
    """Create a weak ETag value."""
    return f'W/"{revision}"'


def extract_etag_revision(etag: str) -> Optional[int]:
    """Extract revision number from an ETag."""
    if not etag or not etag.startswith('W/"') or not etag.endswith('"'):
        return None
    try:
        return int(etag[3:-1])
    except (ValueError, IndexError):
        return None


def check_if_match(required_revision: int) -> bool:
    """Check If-Match header against required revision. Return True if it matches."""
    if_match = request.headers.get("If-Match")
    if not if_match:
        return False

    required_etag = create_etag(required_revision)
    return if_match == required_etag


def check_if_match_conflict(required_revision: int, current_revision: int) -> dict | None:
    """Check If-Match header and return conflict error dict if stale. None = OK.
    
    Args:
        required_revision: The revision the client thinks the resource has (from If-Match)
        current_revision: The actual current revision on the server
    
    Returns:
        Conflict error dict if they don't match, None if OK.
    """
    if required_revision != current_revision:
        # Return conflict with current revision
        return {
            "code": "CONFLICT",
            "status": 409,
            "message": "Resource has been modified since you last read it",
            "details": {
                "current_etag": create_etag(current_revision),
            },
        }
    return None
