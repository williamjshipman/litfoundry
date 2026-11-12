"""Write coordination primitives for background jobs and interactive edits.

Implements:
- Global write barrier (draining, frozen, released)
- Write scopes (append, records, project)
- Per-project write leases
- Active writer registry
- Fenced system leases for maintenance operations
- Exempt operational writes (sign-in, tokens, audit, etc.)
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Barrier and lease constants
BARRIER_DRAIN_TIMEOUT_SECONDS = 120  # Max time to wait for active writers to drain
BARRIER_WAIT_TIMEOUT_SECONDS = 2     # Max time interactive writes wait for barrier
BARRIER_CACHE_TTL = 0.25             # 250ms cache for barrier state


class BarrierFrozen(Exception):
    """Exception raised when barrier is frozen and write times out."""
    pass


class BarrierState:
    """States for the global write barrier."""
    RELEASED = "released"
    DRAINING = "draining"
    FROZEN = "frozen"


class WriteScope:
    """Write scope types for jobs."""
    APPEND = "append"      # New rows only
    RECORDS = "records"    # Listed set of work IDs
    PROJECT = "project"    # Whole project


# Exempt operational tables that bypass the barrier
EXEMPT_OPERATIONAL_TABLES = {
    "job_leases",           # Job lease, heartbeat, progress
    "job_progress",
    "refresh_tokens",       # Session token refresh
    "login_throttle",       # Login rate limiting
    "audit_events",         # Admin audit trail
    "last_sign_in",         # User login tracking
    "system_leases",        # Maintenance operation coordination
    "active_writers",       # Write barrier coordination
    "backup_run_records",   # Backup operation tracking
}


class WriteCoordinator:
    """Coordinates all writes to ensure consistency and prevent conflicts."""

    def __init__(self, catalog_engine: Engine):
        """Initialize write coordinator.
        
        Args:
            catalog_engine: SQLAlchemy engine for the catalogue database
        """
        self.catalog_engine = catalog_engine
        self._barrier_cache: Dict[str, Any] = {}
        self._barrier_cache_time = 0.0

    def _get_barrier_state(self) -> Dict[str, Any]:
        """Get current barrier state with caching.
        
        Returns:
            Dict with keys: state, owner, fencing_token, expires_at
        """
        now = time.time()
        if now - self._barrier_cache_time < BARRIER_CACHE_TTL:
            return self._barrier_cache.get("state", {
                "state": BarrierState.RELEASED,
                "owner": None,
                "fencing_token": 0,
                "expires_at": None,
            })
        
        with self.catalog_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT state, owner, fencing_token, expires_at
                    FROM system_leases
                    WHERE name = 'write-barrier'
                """)
            )
            row = result.fetchone()
            
            if row:
                state_dict = {
                    "state": row[0],
                    "owner": row[1],
                    "fencing_token": row[2],
                    "expires_at": row[3],
                }
            else:
                state_dict = {
                    "state": BarrierState.RELEASED,
                    "owner": None,
                    "fencing_token": 0,
                    "expires_at": None,
                }
        
        self._barrier_cache = {"state": state_dict}
        self._barrier_cache_time = now
        return state_dict

    @contextmanager
    def write_unit(
        self,
        session: Session,
        job_id: Optional[str] = None,
        project_id: Optional[str] = None,
        scope: Optional[str] = None,
        work_ids: Optional[List[str]] = None,
    ):
        """Context manager for a write unit.
        
        Registers as an active writer, checks barrier, and validates write scope conflicts.
        
        Args:
            session: SQLAlchemy session
            job_id: Job ID (None for interactive writes)
            project_id: Project ID
            scope: Write scope (append, records, project) - None for interactive
            work_ids: Work IDs if scope is records
            
        Raises:
            BarrierFrozen: If barrier is frozen and write times out
        """
        writer_id = str(uuid4())
        
        # Register as active writer
        self._register_active_writer(
            writer_id, job_id, project_id, scope, work_ids
        )
        
        try:
            # Check barrier (blocking or timeout)
            self._check_barrier_for_write(timeout_seconds=BARRIER_WAIT_TIMEOUT_SECONDS)
            
            # Check write scope conflicts
            if project_id:
                if scope == WriteScope.RECORDS and work_ids:
                    self._check_record_locks(project_id, work_ids)
                elif scope == WriteScope.PROJECT:
                    self._check_project_busy(project_id)
            
            yield
            
        finally:
            # Unregister active writer
            self._unregister_active_writer(writer_id)

    @contextmanager
    def operational_session(self, session: Session):
        """Context manager for exempt operational writes.
        
        Bypasses barrier checks for sign-in, tokens, audit, etc.
        
        Args:
            session: SQLAlchemy session
        """
        # No checks - just a logical marker
        yield

    def _register_active_writer(
        self,
        writer_id: str,
        job_id: Optional[str] = None,
        project_id: Optional[str] = None,
        scope: Optional[str] = None,
        work_ids: Optional[List[str]] = None,
    ) -> None:
        """Register an active writer.
        
        Args:
            writer_id: Writer registration ID
            job_id: Job ID (None for interactive)
            project_id: Project ID
            scope: Write scope
            work_ids: Work IDs if scope is records
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=600)  # 10 minute timeout
        
        scope_json = None
        if scope == WriteScope.RECORDS and work_ids:
            scope_json = json.dumps({"scope": scope, "work_ids": work_ids})
        elif scope in (WriteScope.APPEND, WriteScope.PROJECT):
            scope_json = json.dumps({"scope": scope})
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO active_writers (
                        id, job_id, project_id, scope_json, registered_at, expires_at
                    ) VALUES (
                        :id, :job_id, :project_id, :scope_json, :registered_at, :expires_at
                    )
                """),
                {
                    "id": writer_id,
                    "job_id": job_id,
                    "project_id": project_id,
                    "scope_json": scope_json,
                    "registered_at": now,
                    "expires_at": expires_at,
                },
            )

    def _unregister_active_writer(self, writer_id: str) -> None:
        """Unregister an active writer.
        
        Args:
            writer_id: Writer registration ID
        """
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM active_writers WHERE id = :id"),
                {"id": writer_id},
            )

    def _check_barrier_for_write(self, timeout_seconds: float = BARRIER_WAIT_TIMEOUT_SECONDS) -> None:
        """Check barrier, waiting briefly if draining, failing if frozen.
        
        Args:
            timeout_seconds: Max seconds to wait for barrier to release
            
        Raises:
            BarrierFrozen: If barrier is frozen after timeout
        """
        barrier_state = self._get_barrier_state()
        
        if barrier_state["state"] == BarrierState.RELEASED:
            return  # No barrier
        
        if barrier_state["state"] == BarrierState.DRAINING:
            # Wait briefly for it to release or freeze
            start = time.time()
            while time.time() - start < timeout_seconds:
                time.sleep(0.1)
                barrier_state = self._get_barrier_state()
                if barrier_state["state"] == BarrierState.RELEASED:
                    return  # Barrier released
        
        # Barrier is frozen or timeout reached
        raise BarrierFrozen()

    def _wait_for_barrier(self) -> None:
        """Wait for barrier to release (for jobs).
        
        Jobs block indefinitely at checkpoints while barrier is raised.
        """
        barrier_state = self._get_barrier_state()
        
        if barrier_state["state"] == BarrierState.RELEASED:
            return  # No barrier
        
        # Block until barrier is released
        while True:
            time.sleep(0.5)
            barrier_state = self._get_barrier_state()
            if barrier_state["state"] == BarrierState.RELEASED:
                return

    def _check_record_locks(self, project_id: str, work_ids: List[str]) -> None:
        """Check if any work IDs are locked by running records jobs.
        
        Raises:
            RuntimeError: If record is locked by another job
        """
        with self.catalog_engine.connect() as conn:
            # Find if any running records/project jobs affect these work IDs
            placeholders = ",".join([f":work_id_{i}" for i in range(len(work_ids))])
            params = {f"work_id_{i}": work_ids[i] for i in range(len(work_ids))}
            params["project_id"] = project_id
            
            # Check for running project jobs (block all records)
            result = conn.execute(
                text(f"""
                    SELECT COUNT(*) FROM jobs j
                    JOIN active_writers aw ON j.id = aw.job_id
                    WHERE j.project_id = :project_id
                        AND j.status = 'running'
                        AND aw.scope_json LIKE '%"scope":"project"%'
                """),
                {"project_id": project_id},
            )
            if result.scalar() > 0:
                raise RuntimeError("PROJECT_BUSY")
            
            # Check for running records jobs with overlapping work IDs
            result = conn.execute(
                text(f"""
                    SELECT COUNT(*) FROM job_locked_works
                    WHERE job_id IN (
                        SELECT j.id FROM jobs j
                        WHERE j.project_id = :project_id
                            AND j.status = 'running'
                    )
                    AND work_id IN ({placeholders})
                """),
                params,
            )
            if result.scalar() > 0:
                raise RuntimeError("RECORD_LOCKED")

    def _check_project_busy(self, project_id: str) -> None:
        """Check if project is busy with another write.
        
        Raises:
            RuntimeError: If project is busy
        """
        with self.catalog_engine.connect() as conn:
            # Check for any running project job
            result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM jobs j
                    WHERE j.project_id = :project_id
                        AND j.status = 'running'
                        AND j.scope_json LIKE '%"scope":"project"%'
                """),
                {"project_id": project_id},
            )
            if result.scalar() > 0:
                raise RuntimeError("PROJECT_BUSY")

    def acquire_system_lease(
        self,
        name: str,
        owner: str,
        duration_seconds: int = 300,
    ) -> int:
        """Acquire a system lease (for maintenance operations).
        
        Returns a new fencing token if lease was acquired or reclaimed.
        
        Args:
            name: Lease name (e.g., "migration", "full-backup")
            owner: Owner identifier (usually worker ID)
            duration_seconds: Lease duration
            
        Returns:
            Fencing token (for stale-lease detection)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=duration_seconds)
        
        with self.catalog_engine.begin() as conn:
            # Check if lease exists
            result = conn.execute(
                text("""
                    SELECT owner, fencing_token, expires_at FROM system_leases
                    WHERE name = :name
                """),
                {"name": name},
            )
            row = result.fetchone()
            
            if row:
                existing_owner, fencing_token, lease_expires = row
                
                # If lease hasn't expired, can't acquire
                if lease_expires and lease_expires > now:
                    raise RuntimeError(f"Lease {name} held by {existing_owner}")
                
                # Lease expired - reclaim with higher fencing token
                new_token = fencing_token + 1
                conn.execute(
                    text("""
                        UPDATE system_leases
                        SET owner = :owner, fencing_token = :token, expires_at = :expires_at
                        WHERE name = :name
                    """),
                    {
                        "name": name,
                        "owner": owner,
                        "token": new_token,
                        "expires_at": expires_at,
                    },
                )
                return new_token
            else:
                # New lease
                conn.execute(
                    text("""
                        INSERT INTO system_leases (name, owner, state, fencing_token, expires_at)
                        VALUES (:name, :owner, :state, :token, :expires_at)
                    """),
                    {
                        "name": name,
                        "owner": owner,
                        "state": BarrierState.RELEASED,
                        "token": 1,
                        "expires_at": expires_at,
                    },
                )
                return 1

    def release_system_lease(self, name: str, fencing_token: int) -> bool:
        """Release a system lease.
        
        Args:
            name: Lease name
            fencing_token: Fencing token (for detection of stale operations)
            
        Returns:
            True if released, False if token mismatch (stale operation)
        """
        with self.catalog_engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE system_leases
                    SET owner = NULL, expires_at = NULL
                    WHERE name = :name AND fencing_token = :token
                """),
                {"name": name, "token": fencing_token},
            )
            return result.rowcount > 0

    def raise_barrier(
        self,
        owner: str,
        fencing_token: int,
    ) -> None:
        """Raise the write barrier to draining state.
        
        Args:
            owner: Lease owner (maintenance operation)
            fencing_token: Fencing token
        """
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE system_leases
                    SET state = :state
                    WHERE name = 'write-barrier' AND owner = :owner AND fencing_token = :token
                """),
                {
                    "state": BarrierState.DRAINING,
                    "owner": owner,
                    "token": fencing_token,
                },
            )

    def freeze_barrier(
        self,
        owner: str,
        fencing_token: int,
        drain_timeout: int = BARRIER_DRAIN_TIMEOUT_SECONDS,
    ) -> bool:
        """Transition barrier from draining to frozen.
        
        Args:
            owner: Lease owner
            fencing_token: Fencing token
            drain_timeout: Max time to wait for active writers to drain
            
        Returns:
            True if frozen, False if timeout (still have active writers)
        """
        start = time.time()
        
        while time.time() - start < drain_timeout:
            with self.catalog_engine.connect() as conn:
                # Count active writers
                result = conn.execute(
                    text("""
                        SELECT COUNT(*) FROM active_writers
                        WHERE expires_at > :now
                    """),
                    {"now": datetime.now(timezone.utc)},
                )
                if result.scalar() == 0:
                    # All writers drained, freeze it
                    with self.catalog_engine.begin() as conn:
                        conn.execute(
                            text("""
                                UPDATE system_leases
                                SET state = :state
                                WHERE name = 'write-barrier' AND owner = :owner AND fencing_token = :token
                            """),
                            {
                                "state": BarrierState.FROZEN,
                                "owner": owner,
                                "token": fencing_token,
                            },
                        )
                    # Clear cache
                    self._barrier_cache_time = 0
                    return True
            
            time.sleep(1)
        
        # Timeout - couldn't freeze
        return False

    def release_barrier(self, owner: str, fencing_token: int) -> None:
        """Release the write barrier back to released state.
        
        Args:
            owner: Lease owner
            fencing_token: Fencing token
        """
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE system_leases
                    SET state = :state
                    WHERE name = 'write-barrier' AND owner = :owner AND fencing_token = :token
                """),
                {
                    "state": BarrierState.RELEASED,
                    "owner": owner,
                    "token": fencing_token,
                },
            )
        # Clear cache
        self._barrier_cache_time = 0
