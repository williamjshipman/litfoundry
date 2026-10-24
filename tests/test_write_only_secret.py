"""Tests for write-only secret field handling."""

import pytest

from litfoundry.write_only_secret import (
    WriteOnlySecret,
    write_only_secret_response,
    merge_write_only_fields,
)


class TestWriteOnlySecret:
    """Tests for WriteOnlySecret class."""

    def test_configured_secret_reports_true(self) -> None:
        """Verify that configured() creates a secret with is_configured=True."""
        secret = WriteOnlySecret.configured()
        assert secret.is_configured is True

    def test_not_configured_secret_reports_false(self) -> None:
        """Verify that not_configured() creates a secret with is_configured=False."""
        secret = WriteOnlySecret.not_configured()
        assert secret.is_configured is False

    def test_with_value_stores_value_internally(self) -> None:
        """Verify that with_value() stores the value but marks as configured."""
        value = b"secret_api_key"
        secret = WriteOnlySecret.with_value(value)

        assert secret.is_configured is True
        assert secret.actual_value == value

    def test_to_dict_returns_only_configured_status(self) -> None:
        """Verify that to_dict never includes the actual value."""
        secret_with_value = WriteOnlySecret.with_value(b"my_secret_key")
        result = secret_with_value.to_dict()

        assert result == {"configured": True}
        assert "actual_value" not in result
        assert "value" not in result

    def test_to_dict_false_configured(self) -> None:
        """Verify that to_dict reports False for unconfigured secrets."""
        secret = WriteOnlySecret.not_configured()
        result = secret.to_dict()

        assert result == {"configured": False}

    def test_repr_never_leaks_value(self) -> None:
        """Verify that repr never includes the actual secret value."""
        secret = WriteOnlySecret.with_value(b"super_secret_password")
        repr_str = repr(secret)

        assert "super_secret_password" not in repr_str
        assert "configured=True" in repr_str

    def test_constructor_direct(self) -> None:
        """Verify direct constructor initialization."""
        secret = WriteOnlySecret(is_configured=True, actual_value=b"key")

        assert secret.is_configured is True
        assert secret.actual_value == b"key"

    def test_constructor_no_value(self) -> None:
        """Verify constructor with no actual value."""
        secret = WriteOnlySecret(is_configured=False)

        assert secret.is_configured is False
        assert secret.actual_value is None


class TestWriteOnlySecretResponse:
    """Tests for write_only_secret_response helper function."""

    def test_configured_returns_true(self) -> None:
        """Verify that configured secrets return {'configured': True}."""
        result = write_only_secret_response(True)

        assert result == {"configured": True}

    def test_not_configured_returns_false(self) -> None:
        """Verify that unconfigured secrets return {'configured': False}."""
        result = write_only_secret_response(False)

        assert result == {"configured": False}

    def test_response_never_includes_secret_value(self) -> None:
        """Verify that response never has any key besides 'configured'."""
        result = write_only_secret_response(True)

        assert len(result) == 1
        assert set(result.keys()) == {"configured"}

    def test_response_with_truthy_value(self) -> None:
        """Verify truthiness is handled correctly."""
        # Non-empty string is truthy
        result = write_only_secret_response("secret_value")
        assert result == {"configured": True}

        # Empty string is falsy
        result = write_only_secret_response("")
        assert result == {"configured": False}

        # None is falsy
        result = write_only_secret_response(None)
        assert result == {"configured": False}


class TestMergeWriteOnlyFields:
    """Tests for merging updates while preserving write-only secrets."""

    def test_merge_with_explicit_new_secret(self) -> None:
        """Verify that explicit new secret values are stored."""
        stored_data = {
            "id": "cred-1",
            "name": "My Credential",
            "api_key": b"old_secret_key",
            "description": "Original description",
        }

        update_data = {
            "name": "Updated Name",
            "api_key": b"new_secret_key",
        }

        secret_fields = ["api_key"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["id"] == "cred-1"
        assert result["name"] == "Updated Name"
        assert result["api_key"] == b"new_secret_key"
        assert result["description"] == "Original description"

    def test_merge_omitting_secret_keeps_stored(self) -> None:
        """Verify that omitting a secret field keeps the stored value."""
        stored_data = {
            "id": "cred-1",
            "name": "My Credential",
            "api_key": b"existing_secret_key",
        }

        update_data = {
            "name": "Updated Name",
            # api_key omitted - should keep existing
        }

        secret_fields = ["api_key"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["name"] == "Updated Name"
        assert result["api_key"] == b"existing_secret_key"

    def test_merge_with_none_secret_keeps_stored(self) -> None:
        """Verify that None values for secrets keep the stored value."""
        stored_data = {
            "id": "cred-1",
            "password": b"stored_password",
        }

        update_data = {
            "password": None,  # Explicitly None - should keep stored
        }

        secret_fields = ["password"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["password"] == b"stored_password"

    def test_merge_multiple_secret_fields(self) -> None:
        """Verify merging with multiple secret fields."""
        stored_data = {
            "id": "config-1",
            "api_key": b"old_api_key",
            "password": b"old_password",
            "region": "us-east-1",
        }

        update_data = {
            "api_key": b"new_api_key",
            "region": "us-west-2",
            # password omitted - should keep
        }

        secret_fields = ["api_key", "password"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["api_key"] == b"new_api_key"
        assert result["password"] == b"old_password"  # Kept
        assert result["region"] == "us-west-2"  # Updated

    def test_merge_non_secret_fields_updated(self) -> None:
        """Verify that non-secret fields are updated normally."""
        stored_data = {
            "id": "cred-1",
            "name": "Original Name",
            "api_key": b"secret",
        }

        update_data = {
            "name": "New Name",
        }

        secret_fields = ["api_key"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["name"] == "New Name"

    def test_merge_empty_update(self) -> None:
        """Verify that empty update keeps all stored data."""
        stored_data = {
            "id": "cred-1",
            "name": "Name",
            "api_key": b"secret",
        }

        update_data = {}
        secret_fields = ["api_key"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result == stored_data

    def test_merge_does_not_modify_original_stored_data(self) -> None:
        """Verify that merge does not modify the input stored_data dict."""
        stored_data = {
            "id": "cred-1",
            "api_key": b"secret",
        }

        stored_data_copy = stored_data.copy()

        update_data = {"name": "new"}
        secret_fields = ["api_key"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        # Original should not be modified
        assert stored_data == stored_data_copy

    def test_merge_active_directory_credentials(self) -> None:
        """Verify real-world scenario: AD service account update."""
        stored_data = {
            "id": "ad-config",
            "enabled": True,
            "server": "ldap://ad.example.com",
            "service_account_username": "litfoundry_svc",
            "service_account_password": b"encrypted_complex_password",
        }

        # Admin updates only the server, leaves password untouched
        update_data = {
            "server": "ldap://ad2.example.com",
        }

        secret_fields = ["service_account_password"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["server"] == "ldap://ad2.example.com"
        assert result["service_account_password"] == b"encrypted_complex_password"

    def test_merge_openAlex_api_key_rotation(self) -> None:
        """Verify real-world scenario: API key rotation."""
        stored_data = {
            "id": "openAlex",
            "name": "OpenAlex API",
            "url": "https://api.openalex.org",
            "api_key": b"encrypted_old_api_key",
        }

        # Admin rotates the API key
        update_data = {
            "api_key": b"encrypted_new_api_key",
        }

        secret_fields = ["api_key"]

        result = merge_write_only_fields(stored_data, update_data, secret_fields)

        assert result["api_key"] == b"encrypted_new_api_key"
        assert result["name"] == "OpenAlex API"
