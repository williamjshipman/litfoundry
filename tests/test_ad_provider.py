"""Unit tests for Active Directory provider."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from litfoundry.auth import ActiveDirectoryProvider
from litfoundry.catalog import User, DirectoryConfig, DirectoryIdentityBinding
from litfoundry.directory import DirectoryConnectionError, DirectorySearchError, DirectoryBindError


@pytest.fixture
def ad_provider():
    """Create an ActiveDirectoryProvider instance."""
    return ActiveDirectoryProvider()


@pytest.fixture
def directory_config():
    """Create a mock DirectoryConfig."""
    config = Mock(spec=DirectoryConfig)
    config.id = 1
    config.enabled = True
    config.domain_controllers_json = '["dc1.example.com:636"]'
    config.base_dn = "dc=example,dc=com"
    config.tls_mode = "ldaps"
    config.connection_timeout_seconds = 5
    config.read_timeout_seconds = 10
    config.service_account_username = "CN=svc_account,CN=Users,DC=example,DC=com"
    config.service_account_password_encrypted = "encrypted_password"
    return config


@pytest.fixture
def test_user():
    """Create a test User."""
    user = Mock(spec=User)
    user.id = 1
    user.username = "jsmith"
    user.account_type = "active_directory"
    user.active = True
    user.last_login_at = None
    return user


@pytest.fixture
def directory_identity_binding(test_user):
    """Create a test DirectoryIdentityBinding."""
    binding = Mock(spec=DirectoryIdentityBinding)
    binding.user_id = test_user.id
    binding.sid = "S-1-5-21-3623811015-3361044348-30300820-1013"
    binding.guid = "12345678-1234-1234-1234-123456789012"
    binding.samaccountname_normalized = "jsmith"
    binding.upn_normalized = "jsmith@example.com"
    return binding


class TestActiveDirectoryProvider:
    """Test suite for ActiveDirectoryProvider."""
    
    def test_provider_name(self, ad_provider):
        """Test provider name is 'active_directory'."""
        assert ad_provider.provider_name == "active_directory"
    
    def test_verify_credentials_rejects_empty_password(self, ad_provider):
        """Test empty password is rejected without any directory call."""
        session = Mock()
        result = ad_provider.verify_credentials("user@example.com", "", session)
        assert result is None
        # Session query should not be called
        session.query.assert_not_called()
    
    def test_verify_credentials_rejects_admin_identifier(self, ad_provider):
        """Test 'admin' identifier is rejected."""
        session = Mock()
        result = ad_provider.verify_credentials("admin", "password", session)
        assert result is None
    
    def test_verify_credentials_rejects_admin_case_insensitive(self, ad_provider):
        """Test 'admin' identifier is rejected (case-insensitive)."""
        session = Mock()
        result = ad_provider.verify_credentials("ADMIN", "password", session)
        assert result is None
        
        result = ad_provider.verify_credentials("Admin", "password", session)
        assert result is None
    
    def test_verify_credentials_no_directory_config(self, ad_provider):
        """Test returns None when DirectoryConfig doesn't exist."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = ad_provider.verify_credentials("user@example.com", "password", session)
        assert result is None
    
    def test_verify_credentials_directory_disabled(self, ad_provider, directory_config):
        """Test returns None when AD is disabled."""
        directory_config.enabled = False
        session = Mock()
        session.query.return_value.filter_by.return_value.first.return_value = directory_config
        
        result = ad_provider.verify_credentials("user@example.com", "password", session)
        assert result is None
    
    def test_verify_credentials_directory_connection_error(self, ad_provider, directory_config, test_user, directory_identity_binding):
        """Test returns None when directory connection fails."""
        session = Mock()
        
        # First query returns config, second returns binding, third returns user
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            mock_client_class.side_effect = DirectoryConnectionError("Connection failed")
            
            result = ad_provider.verify_credentials("user@example.com", "password", session)
            assert result is None
    
    def test_verify_credentials_unprovisioned_user(self, ad_provider, directory_config):
        """Test returns None when user is not in SID binding table."""
        session = Mock()
        
        # First query returns config, second returns no binding
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            None  # No binding found
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("user@example.com", "password", session)
                assert result is None
    
    def test_verify_credentials_disabled_account(self, ad_provider, directory_config, directory_identity_binding):
        """Test returns None when user account is disabled (userAccountControl bit 1)."""
        session = Mock()
        
        # Setup queries
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            None  # No user found (shouldn't reach here)
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                # userAccountControl with bit 1 set (disabled)
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 514,  # 512 (normal) + 2 (disabled)
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("user@example.com", "password", session)
                assert result is None
                # Verify bind_as_user was NOT called
                mock_client.bind_as_user.assert_not_called()
    
    def test_verify_credentials_locked_account(self, ad_provider, directory_config, directory_identity_binding):
        """Test returns None when user account is locked (computed UAC bit 4)."""
        session = Mock()
        
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            None  # No user found (shouldn't reach here)
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                # msDS-User-Account-Control-Computed with bit 4 set (lockout)
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 16  # Lockout bit
                    }
                }
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("user@example.com", "password", session)
                assert result is None
                # Verify bind_as_user was NOT called
                mock_client.bind_as_user.assert_not_called()
    
    def test_verify_credentials_inactive_user(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test returns None when user is inactive in local database."""
        test_user.active = False
        
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("user@example.com", "password", session)
                assert result is None
                # Verify bind_as_user was NOT called (checked account state first)
                mock_client.bind_as_user.assert_not_called()
    
    def test_verify_credentials_user_bind_fails(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test returns None when user bind fails (wrong password)."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client.bind_as_user.side_effect = DirectoryBindError("Invalid password")
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("user@example.com", "password", session)
                assert result is None
    
    def test_verify_credentials_successful_upn(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test successful authentication with UPN identifier."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client.bind_as_user.return_value = True
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("jsmith@example.com", "correct_password", session)
                assert result == test_user
                
                # Verify search was called with UPN filter
                mock_client.connect_and_search.assert_called_once()
                call_args = mock_client.connect_and_search.call_args
                assert "(userPrincipalName=" in call_args[1]["search_filter"]
    
    def test_verify_credentials_successful_domain_name(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test successful authentication with DOMAIN\\name identifier."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client.bind_as_user.return_value = True
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("EXAMPLE\\jsmith", "correct_password", session)
                assert result == test_user
                
                # Verify search was called with sAMAccountName filter
                mock_client.connect_and_search.assert_called_once()
                call_args = mock_client.connect_and_search.call_args
                assert "(sAMAccountName=" in call_args[1]["search_filter"]
    
    def test_verify_credentials_successful_bare_name(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test successful authentication with bare sAMAccountName."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client.bind_as_user.return_value = True
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("jsmith", "correct_password", session)
                assert result == test_user
    
    def test_verify_credentials_updates_last_login(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test successful authentication updates last_login_at."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client.bind_as_user.return_value = True
                mock_client_class.return_value = mock_client
                
                result = ad_provider.verify_credentials("jsmith@example.com", "correct_password", session)
                assert result == test_user
                
                # Verify last_login_at was updated
                assert test_user.last_login_at is not None
                assert isinstance(test_user.last_login_at, datetime)
                session.commit.assert_called_once()
    
    def test_change_password_raises_for_ad_user(self, ad_provider, test_user):
        """Test change_password raises ValueError for AD users."""
        session = Mock()
        
        binding = Mock(spec=DirectoryIdentityBinding)
        binding.user_id = test_user.id
        
        session.query.return_value.filter_by.return_value.first.return_value = binding
        
        with pytest.raises(ValueError, match="Password changes are not allowed"):
            ad_provider.change_password(test_user, "new_password", session)
    
    def test_change_password_for_local_user_no_error(self, ad_provider, test_user):
        """Test change_password doesn't raise for non-AD users."""
        session = Mock()
        
        # No binding found (not an AD user)
        session.query.return_value.filter_by.return_value.first.return_value = None
        
        # Should not raise
        ad_provider.change_password(test_user, "new_password", session)
    
    def test_extract_sid_from_binary(self, ad_provider):
        """Test SID extraction from binary format."""
        # This is a real SID in binary: S-1-5-21-3623811015-3361044348-30300820-1013
        binary_sid = b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5"
        
        sid = ad_provider._extract_sid(binary_sid)
        assert sid is not None
        assert sid.startswith("S-1-5-")
    
    def test_extract_sid_from_string(self, ad_provider):
        """Test SID extraction when already a string."""
        sid_string = "S-1-5-21-3623811015-3361044348-30300820-1013"
        
        sid = ad_provider._extract_sid(sid_string)
        assert sid == sid_string
    
    def test_extract_sid_from_none(self, ad_provider):
        """Test SID extraction with None returns None."""
        sid = ad_provider._extract_sid(None)
        assert sid is None
    
    def test_extract_sid_from_empty_bytes(self, ad_provider):
        """Test SID extraction with empty bytes returns None."""
        sid = ad_provider._extract_sid(b"")
        assert sid is None
    
    def test_convert_binary_sid_to_string(self, ad_provider):
        """Test binary SID to string conversion."""
        # S-1-5-21-3623811015-3361044348-30300820-1013
        binary_sid = b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5"
        
        sid_string = ad_provider._convert_binary_sid_to_string(binary_sid)
        assert sid_string is not None
        assert sid_string.startswith("S-1-5-")
        
        # Parse the result to verify structure
        parts = sid_string.split("-")
        assert len(parts) >= 4  # S, revision, authority, at least one sub-auth
    
    def test_ldap_injection_escaping(self, ad_provider, directory_config, directory_identity_binding, test_user):
        """Test LDAP injection characters are properly escaped."""
        session = Mock()
        session.query.return_value.filter_by.return_value.first.side_effect = [
            directory_config,
            directory_identity_binding,
            test_user
        ]
        
        with patch("litfoundry.auth.ad_provider.DirectoryClient") as mock_client_class:
            with patch("litfoundry.auth.ad_provider.decrypt_secret") as mock_decrypt:
                mock_decrypt.return_value = "decrypted_password"
                
                mock_client = MagicMock()
                mock_client.connect_and_search.return_value = {
                    "dn": "CN=John Smith,CN=Users,DC=example,DC=com",
                    "attributes": {
                        "objectSid": b"\x01\x01\x00\x00\x00\x00\x00\x05\x15\x00\x00\x00\x0f\x1b\x07\xd7\xcc\x2b\xcc\xb8\xfd\x54\x10\xe5",
                        "userAccountControl": 512,
                        "msDS-User-Account-Control-Computed": 0
                    }
                }
                mock_client.bind_as_user.return_value = True
                mock_client_class.return_value = mock_client
                
                # Try to authenticate with LDAP injection characters
                malicious_input = "admin*)(uid=*"
                result = ad_provider.verify_credentials(malicious_input, "password", session)
                
                # Should return None (user not found) but not crash
                assert result is None or result == test_user
                
                # Verify escape_filter_value was called
                mock_client_class.escape_filter_value.assert_called()
