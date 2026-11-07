"""LDAP directory client with TLS validation and connection pooling."""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import ssl

from ldap3 import (
    Server, ServerPool, Connection, ALL_ATTRIBUTES,
    FIRST, NONE, SUBTREE,
)
from ldap3.core.exceptions import (
    LDAPException, LDAPSocketOpenError, LDAPBindError,
    LDAPResponseTimeoutError, LDAPSocketReceiveError,
    LDAPCommunicationError,
)
from ldap3.utils.conv import escape_filter_chars
from ldap3.core.tls import Tls

logger = logging.getLogger(__name__)

# Attribute allowlist for directory searches
ALLOWED_ATTRIBUTES = [
    "sAMAccountName",
    "userPrincipalName",
    "displayName",
    "objectSid",
    "userAccountControl",
    "msDS-User-Account-Control-Computed",
    "objectGUID",
]


class DirectoryConnectionError(Exception):
    """Base exception for directory connection failures."""
    pass


class DirectorySearchError(DirectoryConnectionError):
    """Raised when a search operation fails."""
    pass


class DirectoryBindError(DirectoryConnectionError):
    """Raised when a bind operation fails."""
    pass


class DirectoryClient:
    """Thin wrapper over ldap3 with TLS validation, connection pooling, and secure operations."""

    def __init__(
        self,
        domain_controllers: List[str],
        base_dn: str,
        tls_mode: str,  # 'ldaps' or 'starttls'
        ca_bundle_path: Optional[str] = None,
        connection_timeout: int = 30,
        read_timeout: int = 30,
    ):
        """
        Initialize a directory client.

        Args:
            domain_controllers: List of domain controller hostnames
            base_dn: Base DN for searches (e.g., "dc=example,dc=com")
            tls_mode: 'ldaps' (port 636) or 'starttls' (port 389)
            ca_bundle_path: Path to CA certificate bundle (PEM format)
            connection_timeout: Connect timeout in seconds
            read_timeout: Read timeout in seconds

        Raises:
            DirectoryConnectionError: If TLS configuration is invalid
        """
        if tls_mode not in ("ldaps", "starttls"):
            raise DirectoryConnectionError(
                f"Invalid TLS mode '{tls_mode}'. Must be 'ldaps' or 'starttls'."
            )

        if not domain_controllers:
            raise DirectoryConnectionError("At least one domain controller must be specified")

        self.domain_controllers = domain_controllers
        self.base_dn = base_dn
        self.tls_mode = tls_mode
        self.ca_bundle_path = ca_bundle_path
        self.connection_timeout = connection_timeout
        self.read_timeout = read_timeout

        # Build TLS configuration
        self.tls_obj = None
        if tls_mode == "ldaps" or tls_mode == "starttls":
            try:
                # Only include ca_certs_file if it's provided
                tls_kwargs = {
                    "validate": ssl.CERT_REQUIRED,
                    "version": ssl.PROTOCOL_TLSv1_2,
                }
                if ca_bundle_path:
                    tls_kwargs["ca_certs_file"] = ca_bundle_path
                
                self.tls_obj = Tls(**tls_kwargs)
            except Exception as e:
                raise DirectoryConnectionError(f"Failed to configure TLS: {e}")

        # Build server pool
        self.server_pool = self._build_server_pool()
        self.connection: Optional[Connection] = None

    def _build_server_pool(self) -> ServerPool:
        """Build a server pool with FIRST strategy and active checks."""
        servers = []
        for controller in self.domain_controllers:
            use_ssl = self.tls_mode == "ldaps"
            server = Server(
                controller,
                port=636 if use_ssl else 389,
                use_ssl=use_ssl,
                connect_timeout=self.connection_timeout,
                get_info=NONE,
                tls=self.tls_obj,
            )
            servers.append(server)

        return ServerPool(servers, active=True, strategy=FIRST)

    def connect_and_search(
        self,
        service_account_dn: str,
        service_account_password: str,
        search_filter: str,
        attributes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Connect as service account, execute search, and return result.

        Args:
            service_account_dn: DN of service account (e.g., "CN=SvcAcct,CN=Users,DC=example,DC=com")
            service_account_password: Service account password
            search_filter: LDAP filter (should already have chars escaped)
            attributes: List of attributes to retrieve (defaults to allowlist)

        Returns:
            Dict with keys:
                - dn: Distinguished name of the found entry
                - attributes: Dict of attributes

        Raises:
            DirectorySearchError: If search fails or no entry found
            DirectoryBindError: If service account bind fails
            DirectoryConnectionError: If connection fails
        """
        if attributes is None:
            attributes = ALLOWED_ATTRIBUTES

        try:
            # Create connection
            conn = Connection(
                self.server_pool,
                user=service_account_dn,
                password=service_account_password,
                auto_bind=False,
                auto_referrals=False,
                receive_timeout=self.read_timeout,
            )

            # Handle StartTLS if needed
            if self.tls_mode == "starttls":
                conn.open()
                if not conn.start_tls():
                    raise DirectoryConnectionError("Failed to start TLS")

            # Bind as service account
            if not conn.bind():
                raise DirectoryBindError("Failed to bind as service account")

            # Execute search
            if not conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=attributes,
            ):
                raise DirectorySearchError(f"Search failed: {conn.result}")

            # Get entries
            entries = conn.entries
            if not entries:
                raise DirectorySearchError("No entries found matching search filter")

            if len(entries) > 1:
                raise DirectorySearchError(f"Multiple entries found (expected 1, got {len(entries)})")

            entry = entries[0]

            # Return entry data
            result = {
                "dn": entry.entry_dn,
                "attributes": {},
            }

            # Extract attributes (ldap3 Entry objects have direct attribute access)
            for attr in attributes:
                if attr in entry:
                    result["attributes"][attr] = entry[attr].value if hasattr(entry[attr], "value") else entry[attr]

            conn.unbind()
            return result

        except DirectorySearchError:
            raise
        except DirectoryBindError:
            raise
        except LDAPBindError as e:
            raise DirectoryBindError(f"Bind failed: {e}")
        except (LDAPSocketOpenError, LDAPResponseTimeoutError, LDAPSocketReceiveError) as e:
            raise DirectoryConnectionError(f"Connection failed: {e}")
        except LDAPException as e:
            raise DirectoryConnectionError(f"Directory operation failed: {e}")
        except Exception as e:
            raise DirectoryConnectionError(f"Unexpected error: {e}")

    def bind_as_user(self, user_dn: str, password: str) -> bool:
        """
        Bind as a user to verify credentials.

        Args:
            user_dn: Distinguished name of user
            password: User's password

        Returns:
            True if bind succeeded

        Raises:
            DirectoryBindError: If bind fails or password is empty
            DirectoryConnectionError: If connection fails
        """
        if not password:
            raise DirectoryBindError("Empty password not allowed")

        try:
            # Create a new connection for user bind
            conn = Connection(
                self.server_pool,
                user=user_dn,
                password=password,
                auto_bind=False,
                auto_referrals=False,
                receive_timeout=self.read_timeout,
            )

            # Handle StartTLS if needed
            if self.tls_mode == "starttls":
                conn.open()
                if not conn.start_tls():
                    raise DirectoryConnectionError("Failed to start TLS")

            # Attempt bind
            result = conn.bind()
            conn.unbind()

            if not result:
                raise DirectoryBindError("User bind failed")

            return result

        except LDAPBindError as e:
            raise DirectoryBindError(f"User bind failed: {e}")
        except (LDAPSocketOpenError, LDAPResponseTimeoutError, LDAPSocketReceiveError) as e:
            raise DirectoryConnectionError(f"Connection failed: {e}")
        except DirectoryConnectionError:
            raise
        except Exception as e:
            raise DirectoryConnectionError(f"Unexpected error during user bind: {e}")

    @staticmethod
    def escape_filter_value(value: str) -> str:
        """Escape special characters in LDAP filter values."""
        return escape_filter_chars(value)

    def disconnect(self):
        """Close any open connections."""
        if self.connection:
            try:
                self.connection.unbind()
            except Exception:
                pass
            self.connection = None
