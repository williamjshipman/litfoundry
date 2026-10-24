"""Write-only secret field handling for API responses."""

from typing import Any, Dict, Optional


class WriteOnlySecret:
    """Represents a write-only secret field for API responses.

    Secret fields:
    - Report only whether a value is configured (not the value itself)
    - Never return the actual secret in API responses
    - Allow partial updates: omitting the field keeps the stored value
    """

    def __init__(
        self, is_configured: bool = False, actual_value: Optional[bytes] = None
    ) -> None:
        """Initialize a write-only secret field.

        Args:
            is_configured: Whether a secret value is currently stored
            actual_value: The actual secret bytes (kept in memory, never serialized)
        """
        self.is_configured = is_configured
        self.actual_value = actual_value

    @classmethod
    def configured(cls) -> "WriteOnlySecret":
        """Create a configured secret (has a value, but don't say what it is)."""
        return cls(is_configured=True, actual_value=None)

    @classmethod
    def not_configured(cls) -> "WriteOnlySecret":
        """Create an unconfigured secret (no value stored)."""
        return cls(is_configured=False, actual_value=None)

    @classmethod
    def with_value(cls, value: bytes) -> "WriteOnlySecret":
        """Create a secret with an actual value (for internal use during encryption)."""
        return cls(is_configured=True, actual_value=value)

    def to_dict(self) -> Dict[str, bool]:
        """Serialize to API response (only report configuration status).

        Returns:
            Dictionary with 'configured' key (never includes the actual value)
        """
        return {"configured": self.is_configured}

    def __repr__(self) -> str:
        """Safe repr that never leaks the value."""
        return f"WriteOnlySecret(configured={self.is_configured})"


def write_only_secret_response(is_configured: bool) -> Dict[str, bool]:
    """Helper to create a write-only secret field for API responses.

    Usage in API endpoint:
        credential = db.query(Credential).get(id)
        return {
            'id': credential.id,
            'name': credential.name,
            'api_key': write_only_secret_response(credential.api_key is not None)
        }

    Args:
        is_configured: Whether a secret value is stored

    Returns:
        Dictionary with only 'configured' status, never the value
    """
    return {"configured": bool(is_configured)}


def merge_write_only_fields(stored_data: Dict[str, Any], update_data: Dict[str, Any], secret_fields: list[str]) -> Dict[str, Any]:
    """Merge update data with stored data, keeping secrets when omitted.

    For fields marked as secret:
    - If the update includes a new value, use it
    - If the update omits the field (not in update_data), keep the stored value
    - Never include the actual value in returned data

    Args:
        stored_data: The currently stored data
        update_data: The incoming update data (may omit secret fields)
        secret_fields: List of field names that are write-only secrets

    Returns:
        Merged data with secrets handled appropriately
    """
    result = stored_data.copy()

    for key, value in update_data.items():
        if key in secret_fields:
            # For secret fields, only update if explicitly provided (not None)
            if value is not None:
                result[key] = value
            # If value is None/omitted, keep stored value (already in result)
        else:
            # Non-secret fields: update normally
            result[key] = value

    # For secret fields in update_data that are None, we keep stored value
    # For secret fields NOT in update_data at all, we keep stored value

    return result
