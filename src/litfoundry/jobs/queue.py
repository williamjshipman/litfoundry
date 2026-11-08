"""Background job queue implementation."""

import logging
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from uuid import uuid4
from contextlib import contextmanager

from sqlalchemy import text, and_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from litfoundry.jobs.types import (
    Job, JobStatus, WriteScope, JobProgress, JobResult,
    RetryableError, NonRetryableError
)

logger = logging.getLogger(__name__)

# Lease constants
LEASE_DURATION_SECONDS = 60  # Leases last 60 seconds
HEARTBEAT_INTERVAL_SECONDS = 10  # Heartbeat every 10 seconds
DRAIN_TIMEOUT_SECONDS = 120  # Wait max 120 seconds for active writers to drain

# Concurrency limits
MAX_RUNNING_JOBS_GLOBAL = 20  # Maximum jobs running across all users
MAX_RUNNING_JOBS_PER_USER = 5  # Maximum jobs running per user


class JobCancelled(Exception):
    """Exception raised when a job is cancelled."""
    pass


class BarrierFrozen(Exception):
    """Exception raised when the barrier is raised during a write."""
    pass


class JobContext:
    """Context for a running job."""

    def __init__(
        self,
        job: Job,
        session: Session,
        temp_dir: Path,
        queue: "JobQueue",
        worker_id: str,
    ):
        """Initialize job context.
        
        Args:
            job: The job being executed
            session: SQLAlchemy session for the catalogue database
            temp_dir: Temporary directory for the job
            queue: The job queue
            worker_id: ID of the worker running this job
        """
        self.job = job
        self.session = session
        self.temp_dir = temp_dir
        self.queue = queue
        self.worker_id = worker_id
        self._last_checkpoint = time.time()
        self._last_heartbeat = time.time()
        self.progress_data: Optional[JobProgress] = None

    def checkpoint(self) -> None:
        """Checkpoint the job.
        
        This method:
        - Checks if the job was cancelled
        - Blocks if the barrier is raised
        - Renews the lease if needed
        """
        now = time.time()
        
        # Check if we need to renew the lease
        if now - self._last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
            self.queue._renew_lease(self.job.id, self.worker_id)
            self._last_heartbeat = now
        
        # Check if the job was cancelled
        self.queue._check_cancelled(self.job.id)
        
        # Wait for barrier if it's raised
        self.queue._wait_for_barrier()
        
        self._last_checkpoint = now

    def progress(self, data: JobProgress) -> None:
        """Update job progress.
        
        Args:
            data: Progress data
        """
        self.progress_data = data
        self.queue._update_progress(self.job.id, data)

    def authorize(self, required_role: str = "editor") -> bool:
        """Check if the requester is still authorized.
        
        Args:
            required_role: Required role (editor, viewer, etc.)
            
        Returns:
            True if authorized, False otherwise
        """
        if self.job.project_id is None:
            return True  # System jobs have no project auth requirement
        
        return self.queue._check_authorization(
            self.job.user_id, self.job.project_id, required_role
        )

    def write_unit(
        self,
        operation: str,
        project_id: str,
    ) -> "WriteUnit":
        """Start a write unit.
        
        Args:
            operation: Type of write (append, records, project)
            project_id: Project being written to
            
        Returns:
            Context manager for the write unit
        """
        return WriteUnit(
            self.queue,
            self.job.id,
            project_id,
            operation,
            self.job.scope_json,
        )


class WriteUnit:
    """Context manager for a write operation."""

    def __init__(
        self,
        queue: "JobQueue",
        job_id: str,
        project_id: str,
        operation: str,
        scope_json: Optional[str],
    ):
        """Initialize write unit.
        
        Args:
            queue: The job queue
            job_id: ID of the job performing the write
            project_id: Project being written to
            operation: Type of write (append, records, project)
            scope_json: Scope data (for records scope, contains work_ids)
        """
        self.queue = queue
        self.job_id = job_id
        self.project_id = project_id
        self.operation = operation
        self.scope_json = scope_json
        self.writer_id: Optional[str] = None

    def __enter__(self) -> "WriteUnit":
        """Enter the write unit."""
        # Register as active writer
        self.writer_id = self.queue._register_active_writer(
            self.job_id,
            self.project_id,
            self.operation,
        )
        
        # Check barrier (will block if frozen, raise BarrierFrozen on timeout)
        self.queue._check_barrier_for_write()
        
        # Check write scope conflicts
        if self.operation == "records" and self.scope_json:
            scope_data = json.loads(self.scope_json)
            work_ids = scope_data.get("work_ids", [])
            self.queue._check_record_locks(self.project_id, work_ids)
        elif self.operation == "project":
            self.queue._check_project_busy(self.project_id)
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the write unit."""
        if self.writer_id:
            self.queue._unregister_active_writer(self.writer_id)
        return False


class JobQueue:
    """Background job queue."""

    def __init__(self, catalog_engine: Engine, worker_id: Optional[str] = None):
        """Initialize the job queue.
        
        Args:
            catalog_engine: SQLAlchemy engine for the catalogue database
            worker_id: ID of the worker (auto-generated if not provided)
        """
        self.catalog_engine = catalog_engine
        self.worker_id = worker_id or str(uuid4())
        self._job_handlers: Dict[str, Callable] = {}
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        self._barrier_check_cache: Dict[str, Any] = {}
        self._barrier_cache_time = 0
        self._barrier_cache_ttl = 0.25  # 250ms cache

    def register_handler(
        self,
        job_type: str,
        handler: Callable[[JobContext], JobResult],
    ) -> None:
        """Register a job handler.
        
        Args:
            job_type: Type of job (e.g., "import", "merge")
            handler: Callable that executes the job
        """
        self._job_handlers[job_type] = handler

    def enqueue(
        self,
        job_type: str,
        user_id: str,
        project_id: Optional[str] = None,
        priority: int = 50,
        scope_json: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        correlation_id: Optional[str] = None,
        max_attempts: int = 3,
    ) -> str:
        """Enqueue a job.
        
        Args:
            job_type: Type of job
            user_id: User who requested the job
            project_id: Project (None for system jobs)
            priority: Priority (0-100, higher is first)
            scope_json: Write scope as JSON
            idempotency_key: Client-supplied idempotency key
            correlation_id: Trace correlation ID
            max_attempts: Maximum retry attempts
            
        Returns:
            Job ID
        """
        with self.catalog_engine.begin() as conn:
            job_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            # If idempotency_key is provided, check if we already have this job
            if idempotency_key:
                result = conn.execute(
                    text(
                        "SELECT id FROM jobs WHERE user_id = :user_id AND idempotency_key = :key"
                    ),
                    {"user_id": user_id, "key": idempotency_key},
                )
                existing = result.scalar()
                if existing:
                    return existing
            
            # Insert new job
            conn.execute(
                text(
                    """
                    INSERT INTO jobs (
                        id, project_id, user_id, type, status, scope_json, priority,
                        not_before, attempt, max_attempts, correlation_id, idempotency_key,
                        created_at, updated_at
                    ) VALUES (
                        :id, :project_id, :user_id, :type, :status, :scope_json, :priority,
                        :not_before, :attempt, :max_attempts, :correlation_id, :idempotency_key,
                        :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": job_id,
                    "project_id": project_id,
                    "user_id": user_id,
                    "type": job_type,
                    "status": JobStatus.QUEUED.value,
                    "scope_json": scope_json,
                    "priority": priority,
                    "not_before": now,
                    "attempt": 1,
                    "max_attempts": max_attempts,
                    "correlation_id": correlation_id,
                    "idempotency_key": idempotency_key,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        
        return job_id

    def claim(self) -> Optional[Job]:
        """Claim the next available job.
        
        Uses atomic UPDATE ... SELECT to claim a single job.
        This is safe under SQLite's database-level write lock.
        Respects global and per-user concurrency limits.
        
        Returns:
            Job if one was claimed, None if queue is empty or limits exceeded
        """
        now = datetime.now(timezone.utc)
        
        with self.catalog_engine.begin() as conn:
            # First, reclaim expired leases
            self._reclaim_expired_leases(conn, now)
            
            # Check global concurrency limit before attempting claim
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM jobs WHERE status = :running"
                ),
                {"running": JobStatus.RUNNING.value},
            )
            if result.scalar() >= MAX_RUNNING_JOBS_GLOBAL:
                return None
            
            # Find the next queued job (but don't claim yet if user limit would be exceeded)
            result = conn.execute(
                text(
                    """
                    SELECT id, user_id FROM jobs
                    WHERE status = :queued_status
                        AND not_before <= :now
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """
                ),
                {
                    "queued_status": JobStatus.QUEUED.value,
                    "now": now,
                },
            )
            next_job_row = result.fetchone()
            if not next_job_row:
                return None
            
            job_id, user_id = next_job_row
            
            # Check per-user concurrency limit
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM jobs WHERE user_id = :user_id AND status = :running"
                ),
                {"user_id": user_id, "running": JobStatus.RUNNING.value},
            )
            if result.scalar() >= MAX_RUNNING_JOBS_PER_USER:
                return None
            
            # Atomic claim: update the job with our lease
            result = conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        lease_owner = :lease_owner,
                        lease_expires_at = :lease_expires_at,
                        status = :status,
                        updated_at = :updated_at
                    WHERE id = :id
                        AND lease_owner IS NULL
                    """
                ),
                {
                    "id": job_id,
                    "lease_owner": self.worker_id,
                    "lease_expires_at": now + timedelta(seconds=LEASE_DURATION_SECONDS),
                    "status": JobStatus.RUNNING.value,
                    "updated_at": now,
                },
            )
            
            # If nothing was claimed, someone beat us to it
            if result.rowcount == 0:
                return None
            
            # Get the job we just claimed
            result = conn.execute(
                text("SELECT * FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            row = result.fetchone()
            if not row:
                return None
            
            return self._row_to_job(row)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job if found, None otherwise
        """
        with self.catalog_engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            row = result.fetchone()
            if not row:
                return None
            
            return self._row_to_job(row)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if the job was cancelled, False if already complete
        """
        now = datetime.now(timezone.utc)
        
        with self.catalog_engine.begin() as conn:
            # Get current job status
            result = conn.execute(
                text("SELECT status FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            row = result.fetchone()
            if not row:
                return False
            
            current_status = row[0]
            
            # Move to appropriate terminal state
            if current_status == JobStatus.QUEUED.value:
                new_status = JobStatus.CANCELLED.value
            elif current_status == JobStatus.RUNNING.value:
                new_status = JobStatus.CANCELLING.value
            else:
                # Already in terminal state
                return False
            
            conn.execute(
                text(
                    """
                    UPDATE jobs SET status = :status, updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "status": new_status,
                    "id": job_id,
                    "updated_at": now,
                },
            )
            
            return True

    def mark_completed(
        self,
        job_id: str,
        progress: Optional[JobProgress] = None,
    ) -> None:
        """Mark a job as completed.
        
        Args:
            job_id: Job ID
            progress: Final progress data
        """
        now = datetime.now(timezone.utc)
        progress_json = json.dumps(progress.to_dict()) if progress else None
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        status = :status,
                        progress_json = :progress_json,
                        completed_at = :completed_at,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "status": JobStatus.COMPLETED.value,
                    "progress_json": progress_json,
                    "completed_at": now,
                    "id": job_id,
                    "updated_at": now,
                },
            )

    def mark_failed(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        error_cause: Optional[str] = None,
        is_retryable: bool = False,
    ) -> None:
        """Mark a job as failed.
        
        Args:
            job_id: Job ID
            error_code: Error code
            error_message: Error message (will be redacted)
            error_cause: Typed error cause
            is_retryable: Whether the error is retryable
        """
        now = datetime.now(timezone.utc)
        
        with self.catalog_engine.begin() as conn:
            # Get current job
            result = conn.execute(
                text(
                    """
                    SELECT attempt, max_attempts FROM jobs WHERE id = :id
                    """
                ),
                {"id": job_id},
            )
            row = result.fetchone()
            if not row:
                return
            
            attempt, max_attempts = row
            
            # Decide next status
            if is_retryable and attempt < max_attempts:
                status = JobStatus.QUEUED.value
                next_attempt = attempt + 1
            else:
                status = JobStatus.FAILED.value
                next_attempt = attempt
            
            conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        status = :status,
                        attempt = :attempt,
                        error_code = :error_code,
                        error_message = :error_message,
                        error_cause = :error_cause,
                        completed_at = :completed_at,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "status": status,
                    "attempt": next_attempt,
                    "error_code": error_code,
                    "error_message": error_message,
                    "error_cause": error_cause,
                    "completed_at": now,
                    "id": job_id,
                    "updated_at": now,
                },
            )

    def execute_job(
        self,
        job: Job,
        temp_dir: Path,
    ) -> None:
        """Execute a job.
        
        Args:
            job: Job to execute
            temp_dir: Temporary directory for the job
        """
        if job.type not in self._job_handlers:
            logger.error(f"No handler for job type: {job.type}")
            self.mark_failed(
                job.id,
                "JOB_FAILED",
                f"No handler registered for job type '{job.type}'",
                "HANDLER_NOT_FOUND",
            )
            return
        
        handler = self._job_handlers[job.type]
        
        try:
            # Check authorization before starting
            with self.catalog_engine.connect() as conn:
                if job.project_id and not self._check_authorization_raw(
                    conn, job.user_id, job.project_id, "editor"
                ):
                    self.mark_failed(
                        job.id,
                        "JOB_FAILED",
                        "Permission denied",
                        "FORBIDDEN",
                    )
                    return
            
            # Create job context and execute
            with self.catalog_engine.begin() as conn:
                session = Session(bind=self.catalog_engine)
                ctx = JobContext(
                    job=job,
                    session=session,
                    temp_dir=temp_dir,
                    queue=self,
                    worker_id=self.worker_id,
                )
                
                try:
                    result = handler(ctx)
                    
                    if result.status == JobStatus.COMPLETED:
                        self.mark_completed(job.id, result.progress)
                    elif result.status == JobStatus.PARTIAL:
                        self.mark_partial(job.id, result.progress)
                    elif result.status == JobStatus.FAILED:
                        self.mark_failed(
                            job.id,
                            result.error_code or "JOB_FAILED",
                            result.error_message or "Unknown error",
                            result.error_cause,
                        )
                finally:
                    session.close()
        
        except JobCancelled:
            logger.info(f"Job {job.id} was cancelled")
            self.mark_cancelled(job.id)
        
        except RetryableError as e:
            logger.error(f"Job {job.id} failed with retryable error: {e}")
            self.mark_failed(
                job.id,
                e.error_code,
                str(e),
                is_retryable=True,
            )
        
        except NonRetryableError as e:
            logger.error(f"Job {job.id} failed with non-retryable error: {e}")
            self.mark_failed(
                job.id,
                e.error_code,
                str(e),
                e.error_cause,
            )
        
        except Exception as e:
            logger.exception(f"Job {job.id} failed with exception: {e}")
            self.mark_failed(
                job.id,
                "JOB_FAILED",
                str(e),
                "INTERNAL_ERROR",
            )

    def mark_partial(
        self,
        job_id: str,
        progress: Optional[JobProgress] = None,
    ) -> None:
        """Mark a job as partial (some parts succeeded, some failed).
        
        Args:
            job_id: Job ID
            progress: Final progress data
        """
        now = datetime.now(timezone.utc)
        progress_json = json.dumps(progress.to_dict()) if progress else None
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        status = :status,
                        progress_json = :progress_json,
                        completed_at = :completed_at,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "status": JobStatus.PARTIAL.value,
                    "progress_json": progress_json,
                    "completed_at": now,
                    "id": job_id,
                    "updated_at": now,
                },
            )

    def mark_cancelled(self, job_id: str) -> None:
        """Mark a job as cancelled.
        
        Args:
            job_id: Job ID
        """
        now = datetime.now(timezone.utc)
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        status = :status,
                        completed_at = :completed_at,
                        lease_owner = NULL,
                        lease_expires_at = NULL,
                        updated_at = :updated_at
                    WHERE id = :id
                    """
                ),
                {
                    "status": JobStatus.CANCELLED.value,
                    "completed_at": now,
                    "id": job_id,
                    "updated_at": now,
                },
            )

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job object if found, None otherwise
        """
        with self.catalog_engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            row = result.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def list_jobs(self, user_id: Optional[str] = None, limit: int = 50) -> List[Job]:
        """List jobs, optionally filtered by user.
        
        Args:
            user_id: If provided, list only this user's jobs
            limit: Maximum number of jobs to return
            
        Returns:
            List of Job objects ordered by created_at desc
        """
        with self.catalog_engine.connect() as conn:
            if user_id:
                result = conn.execute(
                    text(
                        "SELECT * FROM jobs WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit"
                    ),
                    {"user_id": user_id, "limit": limit},
                )
            else:
                result = conn.execute(
                    text(
                        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT :limit"
                    ),
                    {"limit": limit},
                )
            
            jobs = []
            for row in result.fetchall():
                jobs.append(self._row_to_job(row))
            return jobs

    def cancel_job(self, job_id: str) -> None:
        """Cancel a job (idempotent).
        
        Moves queued -> cancelled or running -> cancelling.
        The actual transition to cancelled happens at the next checkpoint.
        
        Args:
            job_id: Job ID
        """
        now = datetime.now(timezone.utc)
        
        with self.catalog_engine.begin() as conn:
            # Get current job status
            result = conn.execute(
                text("SELECT status FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            row = result.fetchone()
            if not row:
                return  # Job doesn't exist (already deleted or never was)
            
            current_status = JobStatus(row[0])
            
            # If already cancelled/cancelling, return immediately (idempotent)
            if current_status in (JobStatus.CANCELLED, JobStatus.CANCELLING):
                return
            
            # If completed/failed, can't cancel
            if current_status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.PARTIAL):
                return  # Job already finished
            
            # If queued, move directly to cancelled
            if current_status == JobStatus.QUEUED:
                new_status = JobStatus.CANCELLED
                conn.execute(
                    text(
                        """
                        UPDATE jobs SET
                            status = :status,
                            completed_at = :completed_at,
                            lease_owner = NULL,
                            lease_expires_at = NULL,
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "status": new_status.value,
                        "completed_at": now,
                        "id": job_id,
                        "updated_at": now,
                    },
                )
            
            # If running, move to cancelling
            elif current_status == JobStatus.RUNNING:
                conn.execute(
                    text(
                        """
                        UPDATE jobs SET
                            status = :status,
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "status": JobStatus.CANCELLING.value,
                        "id": job_id,
                        "updated_at": now,
                    },
                )

    # Private helper methods

    def _reclaim_expired_leases(self, conn, now: datetime) -> None:
        """Reclaim expired leases by moving jobs back to queued or failed."""
        # Jobs with expired leases that haven't reached max attempts
        conn.execute(
            text(
                """
                UPDATE jobs SET
                    status = :queued,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    attempt = attempt + 1,
                    updated_at = :now
                WHERE status = :running
                    AND lease_expires_at < :now
                    AND attempt < max_attempts
                """
            ),
            {
                "queued": JobStatus.QUEUED.value,
                "running": JobStatus.RUNNING.value,
                "now": now,
            },
        )
        
        # Jobs with expired leases that have reached max attempts
        conn.execute(
            text(
                """
                UPDATE jobs SET
                    status = :failed,
                    lease_owner = NULL,
                    lease_expires_at = NULL,
                    error_code = :error_code,
                    error_message = :error_message,
                    completed_at = :now,
                    updated_at = :now
                WHERE status = :running
                    AND lease_expires_at < :now
                    AND attempt >= max_attempts
                """
            ),
            {
                "failed": JobStatus.FAILED.value,
                "running": JobStatus.RUNNING.value,
                "error_code": "LEASE_EXPIRED",
                "error_message": "Job lease expired after maximum retry attempts",
                "now": now,
            },
        )

    def _renew_lease(self, job_id: str, worker_id: str) -> None:
        """Renew the lease for a running job."""
        now = datetime.now(timezone.utc)
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        lease_expires_at = :expires_at,
                        updated_at = :now
                    WHERE id = :id
                        AND lease_owner = :owner
                        AND status = :running
                    """
                ),
                {
                    "expires_at": now + timedelta(seconds=LEASE_DURATION_SECONDS),
                    "now": now,
                    "id": job_id,
                    "owner": worker_id,
                    "running": JobStatus.RUNNING.value,
                },
            )

    def _check_cancelled(self, job_id: str) -> None:
        """Check if the job was cancelled and raise JobCancelled if so."""
        with self.catalog_engine.connect() as conn:
            result = conn.execute(
                text("SELECT status FROM jobs WHERE id = :id"),
                {"id": job_id},
            )
            row = result.fetchone()
            if row and row[0] in (JobStatus.CANCELLING.value, JobStatus.CANCELLED.value):
                raise JobCancelled()

    def _update_progress(self, job_id: str, progress: JobProgress) -> None:
        """Update job progress."""
        now = datetime.now(timezone.utc)
        progress_json = json.dumps(progress.to_dict())
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET
                        progress_json = :progress_json,
                        updated_at = :now
                    WHERE id = :id
                    """
                ),
                {
                    "progress_json": progress_json,
                    "now": now,
                    "id": job_id,
                },
            )

    def _check_authorization(
        self,
        user_id: str,
        project_id: str,
        required_role: str,
    ) -> bool:
        """Check if user has required access to project."""
        with self.catalog_engine.connect() as conn:
            return self._check_authorization_raw(conn, user_id, project_id, required_role)

    def _check_authorization_raw(
        self,
        conn,
        user_id: str,
        project_id: str,
        required_role: str,
    ) -> bool:
        """Check authorization using an existing connection."""
        # Admin users always have access
        result = conn.execute(
            text("SELECT role FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()
        if row and row[0] == "admin":
            return True
        
        # Check project ACL
        result = conn.execute(
            text(
                "SELECT role FROM project_acl WHERE project_id = :project_id AND user_id = :user_id"
            ),
            {"project_id": project_id, "user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            return False
        
        # Simple role check (assumes editor includes all previous roles)
        user_role = row[0]
        if required_role == "viewer":
            return user_role in ("viewer", "editor")
        elif required_role == "editor":
            return user_role == "editor"
        
        return False

    def _register_active_writer(
        self,
        job_id: str,
        project_id: str,
        operation: str,
    ) -> str:
        """Register an active writer and return the registration ID."""
        writer_id = str(uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=LEASE_DURATION_SECONDS)
        
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO active_writers (id, job_id, project_id, scope, lease_expires_at, registered_at)
                    VALUES (:id, :job_id, :project_id, :scope, :expires_at, :now)
                    """
                ),
                {
                    "id": writer_id,
                    "job_id": job_id,
                    "project_id": project_id,
                    "scope": operation,
                    "expires_at": expires_at,
                    "now": now,
                },
            )
        
        return writer_id

    def _unregister_active_writer(self, writer_id: str) -> None:
        """Unregister an active writer."""
        with self.catalog_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM active_writers WHERE id = :id"),
                {"id": writer_id},
            )

    def _wait_for_barrier(self) -> None:
        """Wait for the barrier to be released if it's raised."""
        # This is a stub - full barrier implementation is in task 3.3
        pass

    def _check_barrier_for_write(self) -> None:
        """Check barrier for a write operation."""
        # This is a stub - full barrier implementation is in task 3.3
        pass

    def _check_record_locks(self, project_id: str, work_ids: List[str]) -> None:
        """Check if any work IDs are locked by running jobs."""
        # This is a stub - full implementation is in task 3.2
        pass

    def _check_project_busy(self, project_id: str) -> None:
        """Check if the project is busy with another write."""
        # This is a stub - full implementation is in task 3.2
        pass

    def _check_concurrency_limits(self, user_id: str) -> bool:
        """Check if a user has exceeded concurrency limits.
        
        Returns:
            True if limits allow a new job, False if limits exceeded
        """
        with self.catalog_engine.connect() as conn:
            # Check global limit
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM jobs WHERE status = :running"
                ),
                {"running": JobStatus.RUNNING.value},
            )
            global_running = result.scalar()
            if global_running >= MAX_RUNNING_JOBS_GLOBAL:
                logger.warning(
                    f"Global concurrency limit reached ({global_running}/{MAX_RUNNING_JOBS_GLOBAL})"
                )
                return False

            # Check per-user limit
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM jobs WHERE user_id = :user_id AND status = :running"
                ),
                {"user_id": user_id, "running": JobStatus.RUNNING.value},
            )
            user_running = result.scalar()
            if user_running >= MAX_RUNNING_JOBS_PER_USER:
                logger.warning(
                    f"User {user_id} concurrency limit reached ({user_running}/{MAX_RUNNING_JOBS_PER_USER})"
                )
                return False

            return True

    def get_running_jobs_count(self, user_id: Optional[str] = None) -> int:
        """Get the number of running jobs globally or for a user.
        
        Args:
            user_id: If provided, count only this user's jobs
            
        Returns:
            Number of running jobs
        """
        with self.catalog_engine.connect() as conn:
            if user_id:
                result = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM jobs WHERE user_id = :user_id AND status = :running"
                    ),
                    {"user_id": user_id, "running": JobStatus.RUNNING.value},
                )
            else:
                result = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM jobs WHERE status = :running"
                    ),
                    {"running": JobStatus.RUNNING.value},
                )
            return result.scalar()

    @staticmethod
    def _row_to_job(row) -> Job:
        """Convert a database row to a Job object."""
        return Job(
            id=row[0],
            project_id=row[1],
            user_id=row[2],
            type=row[3],
            status=JobStatus(row[4]),
            scope_json=row[5],
            priority=row[6],
            not_before=row[7],
            lease_owner=row[8],
            lease_expires_at=row[9],
            attempt=row[10],
            max_attempts=row[11],
            progress_json=row[12],
            error_code=row[13],
            error_message=row[14],
            error_cause=row[15],
            correlation_id=row[16],
            idempotency_key=row[17],
            created_at=row[18],
            updated_at=row[19],
            started_at=row[20],
            completed_at=row[21],
        )
