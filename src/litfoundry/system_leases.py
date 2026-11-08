"""System-wide lease management for fenced operations."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


class LeaseAlreadyHeldError(Exception):
    """Raised when attempting to acquire a lease that is already held."""
    pass


class LeaseNotHeldError(Exception):
    """Raised when attempting to release a lease that is not held."""
    pass


def acquire_lease(
    session: Session,
    lease_key: str,
    holder_id: str,
    duration_seconds: int = 3600,
    metadata: Optional[dict] = None
) -> None:
    """Acquire a system-wide lease.
    
    Args:
        session: Database session
        lease_key: Unique lease identifier (e.g., "maintenance", "full-backup")
        holder_id: UUID or process ID of the lease holder
        duration_seconds: Lease duration in seconds (default: 1 hour)
        metadata: Optional JSON-serializable metadata
        
    Raises:
        LeaseAlreadyHeldError: If the lease is already held by another process
    """
    import json
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=duration_seconds)
    
    # Check if lease exists and is still valid
    result = session.execute(
        text("""
            SELECT lease_key, holder_id, expires_at
            FROM system_leases
            WHERE lease_key = :lease_key
        """),
        {"lease_key": lease_key}
    ).fetchone()
    
    if result:
        _, existing_holder, existing_expires = result
        
        # If lease exists and hasn't expired, it's held
        if existing_expires > now:
            if existing_holder != holder_id:
                raise LeaseAlreadyHeldError(
                    f"Lease '{lease_key}' is held by {existing_holder}"
                )
            # Same holder is re-acquiring, update expiry
            session.execute(
                text("""
                    UPDATE system_leases
                    SET acquired_at = :acquired_at, expires_at = :expires_at
                    WHERE lease_key = :lease_key
                """),
                {
                    "lease_key": lease_key,
                    "acquired_at": now,
                    "expires_at": expires_at
                }
            )
        else:
            # Lease has expired, take it over
            metadata_json = json.dumps(metadata) if metadata else None
            session.execute(
                text("""
                    UPDATE system_leases
                    SET holder_id = :holder_id, acquired_at = :acquired_at, 
                        expires_at = :expires_at, metadata_json = :metadata_json
                    WHERE lease_key = :lease_key
                """),
                {
                    "lease_key": lease_key,
                    "holder_id": holder_id,
                    "acquired_at": now,
                    "expires_at": expires_at,
                    "metadata_json": metadata_json
                }
            )
    else:
        # Lease doesn't exist, create it
        metadata_json = json.dumps(metadata) if metadata else None
        session.execute(
            text("""
                INSERT INTO system_leases (lease_key, holder_id, acquired_at, expires_at, metadata_json)
                VALUES (:lease_key, :holder_id, :acquired_at, :expires_at, :metadata_json)
            """),
            {
                "lease_key": lease_key,
                "holder_id": holder_id,
                "acquired_at": now,
                "expires_at": expires_at,
                "metadata_json": metadata_json
            }
        )
    
    session.commit()


def release_lease(
    session: Session,
    lease_key: str,
    holder_id: str
) -> None:
    """Release a system-wide lease.
    
    Args:
        session: Database session
        lease_key: Unique lease identifier
        holder_id: UUID or process ID of the lease holder (must match to release)
        
    Raises:
        LeaseNotHeldError: If the lease is not held by the given holder
    """
    # Check that the lease is held by the given holder
    result = session.execute(
        text("""
            SELECT holder_id
            FROM system_leases
            WHERE lease_key = :lease_key
        """),
        {"lease_key": lease_key}
    ).fetchone()
    
    if not result:
        raise LeaseNotHeldError(f"Lease '{lease_key}' does not exist")
    
    existing_holder, = result
    if existing_holder != holder_id:
        raise LeaseNotHeldError(
            f"Lease '{lease_key}' is held by {existing_holder}, not {holder_id}"
        )
    
    # Delete the lease
    session.execute(
        text("DELETE FROM system_leases WHERE lease_key = :lease_key"),
        {"lease_key": lease_key}
    )
    session.commit()


def is_lease_held(session: Session, lease_key: str) -> bool:
    """Check if a lease is currently held.
    
    Args:
        session: Database session
        lease_key: Unique lease identifier
        
    Returns:
        True if the lease is held, False otherwise
    """
    now = datetime.now(timezone.utc)
    
    result = session.execute(
        text("""
            SELECT 1
            FROM system_leases
            WHERE lease_key = :lease_key AND expires_at > :now
        """),
        {"lease_key": lease_key, "now": now}
    ).fetchone()
    
    return result is not None


def get_lease_holder(session: Session, lease_key: str) -> Optional[str]:
    """Get the current holder of a lease.
    
    Args:
        session: Database session
        lease_key: Unique lease identifier
        
    Returns:
        Holder ID if the lease is held, None otherwise
    """
    now = datetime.now(timezone.utc)
    
    result = session.execute(
        text("""
            SELECT holder_id
            FROM system_leases
            WHERE lease_key = :lease_key AND expires_at > :now
        """),
        {"lease_key": lease_key, "now": now}
    ).fetchone()
    
    return result[0] if result else None


def cleanup_expired_leases(session: Session) -> int:
    """Clean up expired leases.
    
    Args:
        session: Database session
        
    Returns:
        Number of leases deleted
    """
    now = datetime.now(timezone.utc)
    
    result = session.execute(
        text("""
            DELETE FROM system_leases
            WHERE expires_at <= :now
        """),
        {"now": now}
    )
    
    session.commit()
    return result.rowcount
