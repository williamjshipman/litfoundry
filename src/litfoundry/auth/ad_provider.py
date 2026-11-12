r"""Active Directory authentication provider."""

import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
import json

from litfoundry.directory import DirectoryClient, DirectoryConnectionError, DirectorySearchError, DirectoryBindError
from litfoundry.secrets import decrypt_secret


class ActiveDirectoryProvider:
    r"""Active Directory / LDAP authentication provider.
    
    Extends IdentityProvider interface with AD-specific authentication logic.
    """
    
    # Minimum time to equalize failed attempts (prevent timing attacks)
    MIN_ATTEMPT_TIME_SECONDS = 0.5
    
    @property
    def provider_name(self) -> str:
        return "active_directory"
    
    def verify_credentials(self, identifier: str, password: str, session: Session) -> Optional:
        r"""Verify AD credentials and return the user if valid and provisioned.
        
        Args:
            identifier: UPN, sAMAccountName, or DOMAIN\username
            password: Plaintext password
            session: SQLAlchemy session
            
        Returns:
            User object if credentials valid and user provisioned, None otherwise
        """
        # Import here to avoid circular imports
        from litfoundry.catalog import User, DirectoryConfig, DirectoryIdentityBinding
        
        start_time = time.time()
        
        try:
            # Reject empty password before any directory call
            if not password:
                self._pad_timing(start_time)
                return None
            
            # Reject admin in any form (admin accounts must use local auth)
            if identifier.lower() == "admin":
                self._pad_timing(start_time)
                return None
            
            # Get AD configuration
            config = session.query(DirectoryConfig).filter_by(id=1).first()
            if not config or not config.enabled:
                self._pad_timing(start_time)
                return None
            
            # Get or create directory client
            try:
                client = DirectoryClient(
                    domain_controllers=json.loads(config.domain_controllers_json),
                    base_dn=config.base_dn,
                    tls_mode=config.tls_mode,
                    connection_timeout=config.connection_timeout_seconds,
                    read_timeout=config.read_timeout_seconds,
                )
            except DirectoryConnectionError:
                self._pad_timing(start_time)
                return None
            
            # Decrypt service account password
            service_account_password = decrypt_secret(config.service_account_password_encrypted)
            
            # Build search filter based on identifier format
            escaped_identifier = DirectoryClient.escape_filter_value(identifier)
            search_filter = self._build_search_filter(identifier, escaped_identifier)
            
            # Search for the user through the service account
            try:
                result = client.connect_and_search(
                    service_account_dn=config.service_account_username,
                    service_account_password=service_account_password,
                    search_filter=search_filter,
                )
                
                user_dn = result["dn"]
                attributes = result["attributes"]
                
            except (DirectorySearchError, DirectoryBindError, DirectoryConnectionError):
                self._pad_timing(start_time)
                return None
            
            # Extract SID from search result
            sid = self._extract_sid(attributes.get("objectSid"))
            if not sid:
                self._pad_timing(start_time)
                return None
            
            # Check SID binding exists
            binding = session.query(DirectoryIdentityBinding).filter_by(sid=sid).first()
            if not binding:
                self._pad_timing(start_time)
                return None
            
            # Load the user
            user = session.query(User).filter_by(id=binding.user_id).first()
            if not user or not user.active:
                self._pad_timing(start_time)
                return None
            
            # Check userAccountControl to verify not disabled or locked
            uac = attributes.get("userAccountControl", 0)
            computed_uac = attributes.get("msDS-User-Account-Control-Computed", 0)
            
            # Bit 1 (0x2) = disabled, Bit 4 (0x10) = lockout
            if (uac & 0x2) or (computed_uac & 0x2) or (computed_uac & 0x10):
                self._pad_timing(start_time)
                return None
            
            # Now bind as the user to verify their password
            try:
                result = client.bind_as_user(user_dn, password)
                if not result:
                    self._pad_timing(start_time)
                    return None
            except DirectoryBindError:
                self._pad_timing(start_time)
                return None
            except DirectoryConnectionError:
                self._pad_timing(start_time)
                return None
            
            # Update last login timestamp
            user.last_login_at = datetime.now(timezone.utc)
            session.commit()
            
            self._pad_timing(start_time)
            return user
        
        except Exception:
            self._pad_timing(start_time)
            return None
    
    def change_password(self, user, new_password: str, session: Session) -> None:
        """Reject password changes for AD users.
        
        Args:
            user: User object
            new_password: New plaintext password
            session: SQLAlchemy session
            
        Raises:
            ValueError: Always, since AD users cannot change passwords locally
        """
        # Import here to avoid circular imports
        from litfoundry.catalog import DirectoryIdentityBinding
        
        # Check if this is an AD user
        binding = session.query(DirectoryIdentityBinding).filter_by(user_id=user.id).first()
        if binding:
            raise ValueError("Password changes are not allowed for Active Directory users")
    
    def _build_search_filter(self, identifier: str, escaped_identifier: str) -> str:
        r"""Build an LDAP search filter based on identifier format.
        
        Supports:
        - DOMAIN\sAMAccountName
        - user@domain.com (UPN)
        - sAMAccountName (bare name, searches in any domain)
        """
        if "\\" in identifier:
            # DOMAIN\sAMAccountName format
            return f"(sAMAccountName={escaped_identifier})"
        elif "@" in identifier:
            # UPN format
            return f"(userPrincipalName={escaped_identifier})"
        else:
            # Bare sAMAccountName - search by sAMAccountName
            return f"(sAMAccountName={escaped_identifier})"
    
    def _extract_sid(self, sid_value) -> Optional[str]:
        """Extract SID from ldap3 raw bytes or string.
        
        ldap3 returns objectSid as bytes in binary format. This method converts
        to string SID format (e.g., "S-1-5-21-...").
        """
        if not sid_value:
            return None
        
        if isinstance(sid_value, bytes):
            # Convert binary SID to string format
            return self._convert_binary_sid_to_string(sid_value)
        elif isinstance(sid_value, str):
            # Already a string SID
            return sid_value
        
        return None
    
    def _convert_binary_sid_to_string(self, binary_sid: bytes) -> str:
        """Convert binary SID to string format.
        
        SID Format (binary):
        - Byte 0: Revision (always 0x01)
        - Byte 1: SubAuthority count (N)
        - Bytes 2-7: Authority (48-bit big-endian)
        - Bytes 8+: SubAuthorities (N * 4-byte little-endian integers)
        """
        if len(binary_sid) < 8:
            return None
        
        revision = binary_sid[0]
        sub_auth_count = binary_sid[1]
        
        if revision != 1:
            return None  # Only revision 1 SIDs are supported
        
        # Extract authority (6 bytes, big-endian)
        authority = int.from_bytes(binary_sid[2:8], byteorder="big")
        
        # Build SID string
        sid_string = f"S-{revision}-{authority}"
        
        # Extract and append sub-authorities (4 bytes each, little-endian)
        offset = 8
        for i in range(sub_auth_count):
            if offset + 4 > len(binary_sid):
                return None  # Corrupted SID
            
            sub_auth = int.from_bytes(binary_sid[offset:offset+4], byteorder="little")
            sid_string += f"-{sub_auth}"
            offset += 4
        
        return sid_string
    
    def _pad_timing(self, start_time: float) -> None:
        """Pad execution time to minimize timing attacks."""
        elapsed = time.time() - start_time
        if elapsed < self.MIN_ATTEMPT_TIME_SECONDS:
            time.sleep(self.MIN_ATTEMPT_TIME_SECONDS - elapsed)
