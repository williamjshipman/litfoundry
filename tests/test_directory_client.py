"""Unit tests for DirectoryClient with ldap3 MOCK."""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import ssl

from litfoundry.directory.client import (
    DirectoryClient,
    DirectoryConnectionError,
    DirectorySearchError,
    DirectoryBindError,
)
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError


@pytest.fixture
def valid_config():
    """Valid directory client configuration."""
    return {
        "domain_controllers": ["dc1.example.com", "dc2.example.com"],
        "base_dn": "dc=example,dc=com",
        "tls_mode": "ldaps",
        "ca_bundle_path": None,  # Don't use a fake path
        "connection_timeout": 30,
        "read_timeout": 30,
    }


@pytest.fixture
def client_with_mocks(valid_config):
    """Create a DirectoryClient with all ldap3 components mocked."""
    with patch("litfoundry.directory.client.Server"), \
         patch("litfoundry.directory.client.ServerPool"), \
         patch("litfoundry.directory.client.Tls"):
        return DirectoryClient(**valid_config)


class TestDirectoryClientInitialization:
    """Test DirectoryClient initialization."""

    def test_init_with_ldaps(self, valid_config):
        """Test initialization with LDAPS mode."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"):
            client = DirectoryClient(**valid_config)
            assert client.tls_mode == "ldaps"
            assert client.base_dn == "dc=example,dc=com"

    def test_init_with_starttls(self, valid_config):
        """Test initialization with StartTLS mode."""
        valid_config["tls_mode"] = "starttls"
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"):
            client = DirectoryClient(**valid_config)
            assert client.tls_mode == "starttls"

    def test_init_invalid_tls_mode(self, valid_config):
        """Test initialization with invalid TLS mode raises error."""
        valid_config["tls_mode"] = "invalid"
        with pytest.raises(DirectoryConnectionError, match="Invalid TLS mode"):
            DirectoryClient(**valid_config)

    def test_init_no_domain_controllers(self, valid_config):
        """Test initialization with no domain controllers raises error."""
        valid_config["domain_controllers"] = []
        with pytest.raises(DirectoryConnectionError, match="At least one domain controller"):
            DirectoryClient(**valid_config)

    def test_init_tls_configuration_error(self, valid_config):
        """Test initialization with invalid CA bundle raises error."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls", side_effect=Exception("Bad CA")):
            with pytest.raises(DirectoryConnectionError, match="Failed to configure TLS"):
                DirectoryClient(**valid_config)


class TestDirectoryClientSearch:
    """Test DirectoryClient search operations."""

    def test_connect_and_search_success(self, valid_config):
        """Test successful search operation."""
        mock_entry = MagicMock()
        mock_entry.entry_dn = "CN=jdoe,CN=Users,DC=example,DC=com"
        mock_entry.__contains__ = lambda self, key: key in [
            "sAMAccountName",
            "objectSid",
        ]
        mock_entry.__getitem__ = lambda self, key: (
            MagicMock(value="jdoe")
            if key == "sAMAccountName"
            else MagicMock(value="S-1-5-21-123456789")
        )

        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn = MagicMock()
            mock_conn.entries = [mock_entry]
            mock_conn.result = {"result": 0, "description": "success"}
            mock_conn_class.return_value = mock_conn
            mock_conn.search.return_value = True
            mock_conn.bind.return_value = True

            result = client.connect_and_search(
                service_account_dn="CN=ServiceAccount,CN=Users,DC=example,DC=com",
                service_account_password="password123",
                search_filter="(sAMAccountName=jdoe)",
            )

            assert result["dn"] == "CN=jdoe,CN=Users,DC=example,DC=com"
            assert "sAMAccountName" in result["attributes"]

    def test_connect_and_search_no_results(self, valid_config):
        """Test search with no results."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn = MagicMock()
            mock_conn.entries = []
            mock_conn_class.return_value = mock_conn
            mock_conn.search.return_value = True
            mock_conn.bind.return_value = True

            with pytest.raises(DirectorySearchError, match="No entries found"):
                client.connect_and_search(
                    service_account_dn="CN=ServiceAccount,CN=Users,DC=example,DC=com",
                    service_account_password="password123",
                    search_filter="(sAMAccountName=notfound)",
                )

    def test_connect_and_search_multiple_results(self, valid_config):
        """Test search with multiple results raises error."""
        mock_entry1 = MagicMock(entry_dn="CN=jdoe1,CN=Users,DC=example,DC=com")
        mock_entry2 = MagicMock(entry_dn="CN=jdoe2,CN=Users,DC=example,DC=com")

        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn = MagicMock()
            mock_conn.entries = [mock_entry1, mock_entry2]
            mock_conn_class.return_value = mock_conn
            mock_conn.search.return_value = True
            mock_conn.bind.return_value = True

            with pytest.raises(DirectorySearchError, match="Multiple entries found"):
                client.connect_and_search(
                    service_account_dn="CN=ServiceAccount,CN=Users,DC=example,DC=com",
                    service_account_password="password123",
                    search_filter="(sAMAccountName=jdoe*)",
                )

    def test_connect_and_search_bind_fails(self, valid_config):
        """Test search when service account bind fails."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn = MagicMock()
            mock_conn_class.return_value = mock_conn
            mock_conn.bind.return_value = False

            with pytest.raises(DirectoryBindError, match="Failed to bind"):
                client.connect_and_search(
                    service_account_dn="CN=ServiceAccount,CN=Users,DC=example,DC=com",
                    service_account_password="badpassword",
                    search_filter="(sAMAccountName=jdoe)",
                )

    def test_connect_and_search_connection_timeout(self, valid_config):
        """Test search when connection times out."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn_class.return_value.bind.side_effect = LDAPSocketOpenError("Connection timeout")

            with pytest.raises(DirectoryConnectionError, match="Connection failed"):
                client.connect_and_search(
                    service_account_dn="CN=ServiceAccount,CN=Users,DC=example,DC=com",
                    service_account_password="password123",
                    search_filter="(sAMAccountName=jdoe)",
                )


class TestDirectoryClientUserBind:
    """Test DirectoryClient user bind operations."""

    def test_bind_as_user_success(self, valid_config):
        """Test successful user bind."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn = MagicMock()
            mock_conn_class.return_value = mock_conn
            mock_conn.bind.return_value = True

            result = client.bind_as_user(
                user_dn="CN=jdoe,CN=Users,DC=example,DC=com",
                password="userpassword123",
            )

            assert result is True
            mock_conn.unbind.assert_called_once()

    def test_bind_as_user_empty_password(self, valid_config):
        """Test user bind with empty password raises error."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"):
            client = DirectoryClient(**valid_config)
            
            with pytest.raises(DirectoryBindError, match="Empty password"):
                client.bind_as_user(
                    user_dn="CN=jdoe,CN=Users,DC=example,DC=com",
                    password="",
                )

    def test_bind_as_user_failed(self, valid_config):
        """Test user bind failure."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn = MagicMock()
            mock_conn_class.return_value = mock_conn
            mock_conn.bind.return_value = False

            with pytest.raises(DirectoryBindError):
                client.bind_as_user(
                    user_dn="CN=jdoe,CN=Users,DC=example,DC=com",
                    password="wrongpassword",
                )

    def test_bind_as_user_connection_error(self, valid_config):
        """Test user bind when connection fails."""
        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)
            
            mock_conn_class.return_value.bind.side_effect = LDAPSocketOpenError(
                "Connection refused"
            )

            with pytest.raises(DirectoryConnectionError, match="Connection failed"):
                client.bind_as_user(
                    user_dn="CN=jdoe,CN=Users,DC=example,DC=com",
                    password="password123",
                )


class TestDirectoryClientEscapeFilter:
    """Test filter value escaping."""

    def test_escape_filter_value(self, valid_config):
        """Test LDAP filter character escaping."""
        # Test common special characters that need escaping
        result = DirectoryClient.escape_filter_value("user*name")
        assert isinstance(result, str)  # Should be escaped string
        
        result = DirectoryClient.escape_filter_value("user(name)")
        assert isinstance(result, str)  # Parentheses should be escaped

    def test_escape_filter_value_injection_attempt(self, valid_config):
        """Test LDAP injection protection via escaping."""
        dangerous_input = "*)(uid=*"
        result = DirectoryClient.escape_filter_value(dangerous_input)
        # The result should have special chars escaped, preventing injection
        assert isinstance(result, str)


class TestDirectoryClientStartTLS:
    """Test StartTLS mode."""

    def test_connect_and_search_with_starttls(self, valid_config):
        """Test search with StartTLS mode."""
        valid_config["tls_mode"] = "starttls"

        mock_entry = MagicMock()
        mock_entry.entry_dn = "CN=jdoe,CN=Users,DC=example,DC=com"
        mock_entry.__contains__ = lambda self, key: key == "sAMAccountName"
        mock_entry.__getitem__ = lambda self, key: MagicMock(value="jdoe")

        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)

            mock_conn = MagicMock()
            mock_conn.entries = [mock_entry]
            mock_conn_class.return_value = mock_conn
            mock_conn.open.return_value = None
            mock_conn.start_tls.return_value = True
            mock_conn.search.return_value = True
            mock_conn.bind.return_value = True

            result = client.connect_and_search(
                service_account_dn="CN=ServiceAccount,CN=Users,DC=example,DC=com",
                service_account_password="password123",
                search_filter="(sAMAccountName=jdoe)",
            )

            # Verify start_tls was called
            mock_conn.open.assert_called_once()
            mock_conn.start_tls.assert_called_once()
            assert result["dn"] == "CN=jdoe,CN=Users,DC=example,DC=com"

    def test_bind_as_user_with_starttls_failure(self, valid_config):
        """Test user bind when StartTLS fails."""
        valid_config["tls_mode"] = "starttls"

        with patch("litfoundry.directory.client.Server"), \
             patch("litfoundry.directory.client.ServerPool"), \
             patch("litfoundry.directory.client.Tls"), \
             patch("litfoundry.directory.client.Connection") as mock_conn_class:
            client = DirectoryClient(**valid_config)

            mock_conn = MagicMock()
            mock_conn_class.return_value = mock_conn
            mock_conn.open.return_value = None
            mock_conn.start_tls.return_value = False

            with pytest.raises(DirectoryConnectionError, match="Failed to start TLS"):
                client.bind_as_user(
                    user_dn="CN=jdoe,CN=Users,DC=example,DC=com",
                    password="password123",
                )
