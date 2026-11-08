"""Tests for system leases."""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from litfoundry.system_leases import (
    acquire_lease,
    release_lease,
    is_lease_held,
    get_lease_holder,
    cleanup_expired_leases,
    LeaseAlreadyHeldError,
    LeaseNotHeldError,
)


class TestLeaseAcquisition:
    """Tests for acquiring leases."""
    
    def test_acquire_new_lease(self, catalog_session):
        """Test acquiring a new lease."""
        lease_key = "test-lease"
        holder_id = str(uuid4())
        
        # Should not raise
        acquire_lease(catalog_session, lease_key, holder_id)
        
        # Verify lease is held
        assert is_lease_held(catalog_session, lease_key)
        assert get_lease_holder(catalog_session, lease_key) == holder_id
    
    def test_acquire_held_lease_same_holder(self, catalog_session):
        """Test re-acquiring a lease by the same holder."""
        lease_key = "test-lease"
        holder_id = str(uuid4())
        
        # Acquire initially
        acquire_lease(catalog_session, lease_key, holder_id)
        
        # Re-acquire - should update expiry
        acquire_lease(catalog_session, lease_key, holder_id)
        
        # Should still be held
        assert is_lease_held(catalog_session, lease_key)
        assert get_lease_holder(catalog_session, lease_key) == holder_id
    
    def test_acquire_held_lease_different_holder(self, catalog_session):
        """Test acquiring a lease held by another process."""
        lease_key = "test-lease"
        holder1 = str(uuid4())
        holder2 = str(uuid4())
        
        # Acquire with holder 1
        acquire_lease(catalog_session, lease_key, holder1)
        
        # Try to acquire with holder 2 - should raise
        with pytest.raises(LeaseAlreadyHeldError):
            acquire_lease(catalog_session, lease_key, holder2)
    
    def test_acquire_expired_lease(self, catalog_session):
        """Test acquiring an expired lease."""
        lease_key = "test-lease"
        holder1 = str(uuid4())
        holder2 = str(uuid4())
        
        # Acquire with very short duration
        acquire_lease(catalog_session, lease_key, holder1, duration_seconds=1)
        
        # Wait for expiry (in real code, would wait)
        # For test, update expires_at directly
        from sqlalchemy import text
        now = datetime.now(timezone.utc)
        catalog_session.execute(
            text("UPDATE system_leases SET expires_at = :expires_at WHERE lease_key = :key"),
            {"expires_at": now - timedelta(seconds=1), "key": lease_key}
        )
        catalog_session.commit()
        
        # Should be able to acquire now
        acquire_lease(catalog_session, lease_key, holder2)
        assert get_lease_holder(catalog_session, lease_key) == holder2
    
    def test_acquire_with_metadata(self, catalog_session):
        """Test acquiring a lease with metadata."""
        lease_key = "test-lease"
        holder_id = str(uuid4())
        metadata = {"run_id": str(uuid4()), "version": 1}
        
        acquire_lease(catalog_session, lease_key, holder_id, metadata=metadata)
        
        # Verify metadata was stored
        from sqlalchemy import text
        result = catalog_session.execute(
            text("SELECT metadata_json FROM system_leases WHERE lease_key = :key"),
            {"key": lease_key}
        ).scalar()
        
        import json
        assert json.loads(result) == metadata


class TestLeaseRelease:
    """Tests for releasing leases."""
    
    def test_release_lease(self, catalog_session):
        """Test releasing a lease."""
        lease_key = "test-lease"
        holder_id = str(uuid4())
        
        # Acquire
        acquire_lease(catalog_session, lease_key, holder_id)
        
        # Release
        release_lease(catalog_session, lease_key, holder_id)
        
        # Should no longer be held
        assert not is_lease_held(catalog_session, lease_key)
    
    def test_release_nonexistent_lease(self, catalog_session):
        """Test releasing a nonexistent lease."""
        lease_key = "nonexistent"
        holder_id = str(uuid4())
        
        with pytest.raises(LeaseNotHeldError):
            release_lease(catalog_session, lease_key, holder_id)
    
    def test_release_held_by_different_holder(self, catalog_session):
        """Test releasing a lease held by a different holder."""
        lease_key = "test-lease"
        holder1 = str(uuid4())
        holder2 = str(uuid4())
        
        # Acquire with holder 1
        acquire_lease(catalog_session, lease_key, holder1)
        
        # Try to release with holder 2
        with pytest.raises(LeaseNotHeldError):
            release_lease(catalog_session, lease_key, holder2)


class TestLeaseInquiry:
    """Tests for checking lease status."""
    
    def test_is_lease_held(self, catalog_session):
        """Test checking if a lease is held."""
        lease_key = "test-lease"
        holder_id = str(uuid4())
        
        # Initially not held
        assert not is_lease_held(catalog_session, lease_key)
        
        # Acquire
        acquire_lease(catalog_session, lease_key, holder_id)
        
        # Now held
        assert is_lease_held(catalog_session, lease_key)
    
    def test_get_lease_holder(self, catalog_session):
        """Test getting the holder of a lease."""
        lease_key = "test-lease"
        holder_id = str(uuid4())
        
        # No holder initially
        assert get_lease_holder(catalog_session, lease_key) is None
        
        # Acquire
        acquire_lease(catalog_session, lease_key, holder_id)
        
        # Now has holder
        assert get_lease_holder(catalog_session, lease_key) == holder_id


class TestLeaseCleanup:
    """Tests for cleaning up expired leases."""
    
    def test_cleanup_expired_leases(self, catalog_session):
        """Test cleaning up expired leases."""
        # Create an expired lease
        from sqlalchemy import text
        from uuid import uuid4
        
        lease_key = "expired-lease"
        holder_id = str(uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now - timedelta(seconds=1)
        
        catalog_session.execute(
            text("""
                INSERT INTO system_leases (lease_key, holder_id, acquired_at, expires_at)
                VALUES (:key, :holder, :acquired, :expires)
            """),
            {
                "key": lease_key,
                "holder": holder_id,
                "acquired": now,
                "expires": expires_at
            }
        )
        catalog_session.commit()
        
        # Cleanup
        count = cleanup_expired_leases(catalog_session)
        
        assert count == 1
        assert not is_lease_held(catalog_session, lease_key)
    
    def test_cleanup_valid_leases_not_removed(self, catalog_session):
        """Test that valid leases are not cleaned up."""
        lease_key = "valid-lease"
        holder_id = str(uuid4())
        
        # Create a valid lease
        acquire_lease(catalog_session, lease_key, holder_id, duration_seconds=3600)
        
        # Cleanup
        count = cleanup_expired_leases(catalog_session)
        
        assert count == 0
        assert is_lease_held(catalog_session, lease_key)
