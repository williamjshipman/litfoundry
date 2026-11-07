"""Bootstrap token generation and verification for first-run setup."""

import base64
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple

from litfoundry.auth import get_password_hasher


# Bootstrap token TTL: 30 minutes
BOOTSTRAP_TOKEN_TTL_MINUTES = 30


def generate_bootstrap_token() -> str:
    """Generate a new bootstrap token (32 random bytes, base32 encoded).
    
    Returns:
        Base32-encoded token string (readable format)
    """
    random_bytes = secrets.token_bytes(32)
    # base32 encode and strip padding for cleaner display
    token = base64.b32encode(random_bytes).decode('ascii').rstrip('=')
    return token


def hash_bootstrap_token(token: str) -> str:
    """Hash a bootstrap token using the same hasher as passwords.
    
    Args:
        token: Plain bootstrap token
        
    Returns:
        Argon2 hash of the token
    """
    hasher = get_password_hasher()
    return hasher.hash(token)


def verify_bootstrap_token(token: str, token_hash: str) -> bool:
    """Verify a bootstrap token against its hash.
    
    Args:
        token: Plain bootstrap token to verify
        token_hash: Stored Argon2 hash
        
    Returns:
        True if token matches hash, False otherwise
    """
    hasher = get_password_hasher()
    try:
        hasher.verify(token_hash, token)
        return True
    except Exception:
        return False


def write_bootstrap_token_file(data_root: Path, token: str) -> Path:
    """Write bootstrap token to a restricted file in the data root.
    
    The file is created with permissions that only the service and
    system administrators can read (0o600 on Unix, restricted ACL on Windows).
    
    Args:
        data_root: Data root directory path
        token: Bootstrap token to write
        
    Returns:
        Path to the token file
    """
    token_file = data_root / "bootstrap-token.txt"
    
    # Write token file
    token_file.write_text(token, encoding='utf-8')
    
    # Restrict permissions to owner only (0o600 on Unix)
    # On Windows, the file inherits ACL from data_root which should be restricted
    if os.name == 'posix':
        os.chmod(token_file, 0o600)
    
    return token_file


def delete_bootstrap_token_file(data_root: Path) -> bool:
    """Delete the bootstrap token file if it exists.
    
    Args:
        data_root: Data root directory path
        
    Returns:
        True if file was deleted, False if it didn't exist
    """
    token_file = data_root / "bootstrap-token.txt"
    if token_file.exists():
        token_file.unlink()
        return True
    return False


def read_bootstrap_token_file(data_root: Path) -> Optional[str]:
    """Read the bootstrap token from file if it exists.
    
    Args:
        data_root: Data root directory path
        
    Returns:
        Token string if file exists and is readable, None otherwise
    """
    token_file = data_root / "bootstrap-token.txt"
    if token_file.exists():
        try:
            return token_file.read_text(encoding='utf-8').strip()
        except Exception:
            return None
    return None


def get_bootstrap_token_expiry_time(issued_at: datetime) -> datetime:
    """Calculate the expiry time for a bootstrap token.
    
    Args:
        issued_at: When the token was issued
        
    Returns:
        Expiry time (issued_at + TTL)
    """
    return issued_at + timedelta(minutes=BOOTSTRAP_TOKEN_TTL_MINUTES)


def is_bootstrap_token_expired(expires_at: datetime) -> bool:
    """Check if a bootstrap token has expired.
    
    Args:
        expires_at: Token expiry time (can be naive or timezone-aware)
        
    Returns:
        True if expired, False otherwise
    """
    now = datetime.now(timezone.utc)
    
    # Ensure we're comparing like with like
    if expires_at.tzinfo is None:
        # expires_at is naive, make now naive too
        return now.replace(tzinfo=None) >= expires_at
    else:
        # expires_at is aware, ensure now is too
        return now >= expires_at
