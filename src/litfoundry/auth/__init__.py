"""Authentication and identity providers."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import argon2
from sqlalchemy.orm import Session

from litfoundry.catalog import User


# Argon2id password hasher configured with secure defaults
_password_hasher = argon2.PasswordHasher(
    time_cost=2,          # 2 iterations
    memory_cost=65536,    # 64 MB
    parallelism=4,        # 4 parallelism
    hash_len=16,          # 128 bits
    salt_len=16,          # 128 bits
)

# Dummy hash for timing equalization - created from a dummy password with the hasher
# This is just a valid Argon2 hash that we'll never match but will take time to verify
_dummy_hash = (
    "$argon2id$v=19$m=65536,t=2,p=4$"
    "0000000000000000000000000000000=$"
    "0000000000000000000000000000000="
)


class IdentityProvider(ABC):
    """Abstract interface for authentication providers (local, AD, LDAP, etc)."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'local', 'active_directory')."""
        pass
    
    @abstractmethod
    def verify_credentials(self, identifier: str, password: str, session: Session) -> Optional[User]:
        """Verify login credentials and return the user if valid, or None.
        
        Args:
            identifier: Username or identifier (provider-specific)
            password: Plaintext password
            session: SQLAlchemy session for database access
            
        Returns:
            User object if credentials valid, None otherwise
            
        Raises:
            ValueError: If identifier is invalid format
        """
        pass
    
    @abstractmethod
    def change_password(self, user: User, new_password: str, session: Session) -> None:
        """Change password for a user.
        
        Args:
            user: User object
            new_password: New plaintext password
            session: SQLAlchemy session
            
        Raises:
            ValueError: If password is invalid
        """
        pass


class LocalProvider(IdentityProvider):
    """Local username/password authentication provider."""
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    def verify_credentials(self, identifier: str, password: str, session: Session) -> Optional[User]:
        """Verify local username/password credentials.
        
        Uses timing-equalized password verification to prevent username enumeration.
        Automatically rehashes password if Argon2 parameters change.
        
        Args:
            identifier: Username (case-insensitive)
            password: Plaintext password
            session: SQLAlchemy session
            
        Returns:
            User if credentials valid and account active, None otherwise
        """
        if not identifier or not password:
            # Still verify against dummy hash to equalize timing
            try:
                _password_hasher.verify(_dummy_hash, password)
            except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.InvalidHash, argon2.exceptions.VerificationError):
                pass
            return None
        
        # Normalize username (lowercase for local accounts)
        username_normalized = identifier.lower().strip()
        
        # Look up user by normalized username
        user = session.query(User).filter_by(
            account_type="local",
            username_normalized=username_normalized
        ).first()
        
        if not user or not user.active or not user.password_hash:
            # Account not found or inactive: verify against dummy hash for timing
            try:
                _password_hasher.verify(_dummy_hash, password)
            except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.InvalidHash, argon2.exceptions.VerificationError):
                pass
            return None
        
        # Verify password
        try:
            _password_hasher.verify(user.password_hash, password)
        except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.InvalidHash, argon2.exceptions.VerificationError):
            return None
        
        # Check if hash needs rehashing (Argon2 parameters changed)
        if _password_hasher.check_needs_rehash(user.password_hash):
            user.password_hash = _password_hasher.hash(password)
            session.add(user)
            # Don't commit here; caller handles transaction
        
        return user
    
    def change_password(self, user: User, new_password: str, session: Session) -> None:
        """Change password for a local user.
        
        Args:
            user: User object
            new_password: New plaintext password
            session: SQLAlchemy session
            
        Raises:
            ValueError: If new password is invalid
        """
        if not new_password:
            raise ValueError("Password cannot be empty")
        
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        user.password_hash = _password_hasher.hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        session.add(user)


def get_password_hasher():
    """Return the configured Argon2id password hasher.
    
    This allows external code to hash passwords with the same parameters.
    """
    return _password_hasher


def create_user_with_password(
    user_id: str,
    username: str,
    password: str,
    role: Optional[str] = None,
    account_type: str = "local",
) -> User:
    """Create a new local user with password hash.
    
    Args:
        user_id: UUID for the user
        username: Username
        password: Plaintext password
        role: Optional role ('admin', etc)
        account_type: Account type (default 'local')
        
    Returns:
        User object with hashed password
    """
    now = datetime.now(timezone.utc)
    user = User(
        id=user_id,
        account_type=account_type,
        username=username,
        username_normalized=username.lower().strip(),
        password_hash=_password_hasher.hash(password),
        role=role,
        active=True,
        session_version=0,
        must_change_password=False,
        created_at=now,
        updated_at=now,
    )
    return user
