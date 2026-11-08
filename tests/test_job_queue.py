"""Tests for JobQueue implementation."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import time

import pytest
from sqlalchemy import text

from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade
from litfoundry.jobs import (
    JobQueue, JobStatus, JobProgress, JobResult, JobContext,
    RetryableError, NonRetryableError, JobCancelled
)


@pytest.fixture
def catalog_path():
    """Create a temporary catalog database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog_path = Path(tmpdir) / "catalog.sqlite"
        run_alembic_upgrade(catalog_path, target_revision="head")
        yield catalog_path


@pytest.fixture
def engine(catalog_path):
    """Create a catalog engine."""
    engine = create_catalog_engine(catalog_path)
    yield engine
    engine.dispose()


@pytest.fixture
def queue(engine):
    """Create a job queue."""
    return JobQueue(engine, worker_id="test-worker-1")


@pytest.fixture
def setup_users(engine):
    """Create test users in the database."""
    now = datetime.now(timezone.utc)
    
    with engine.begin() as conn:
        # Create users table
        user_id = str(uuid4())
        conn.execute(
            text(
                """
                INSERT INTO users (id, account_type, username, username_normalized, 
                                   password_hash, must_change_password, role, active, 
                                   session_version, created_at, updated_at)
                VALUES (:id, :account_type, :username, :username_normalized,
                        :password_hash, :must_change_password, :role, :active,
                        :session_version, :created_at, :updated_at)
                """
            ),
            {
                "id": user_id,
                "account_type": "local",
                "username": "testuser",
                "username_normalized": "testuser",
                "password_hash": "$argon2id$...",
                "must_change_password": False,
                "role": "user",
                "active": True,
                "session_version": 0,
                "created_at": now,
                "updated_at": now,
            },
        )
    
    return user_id


class TestJobQueueEnqueue:
    """Test job enqueueing."""

    def test_enqueue_creates_job(self, queue, setup_users, engine):
        """Test that enqueue creates a new job."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id, priority=50)
        
        assert job_id is not None
        
        # Verify job exists in database
        job = queue.get_job(job_id)
        assert job is not None
        assert job.type == "test_job"
        assert job.user_id == user_id
        assert job.status == JobStatus.QUEUED

    def test_enqueue_with_idempotency_returns_existing_job(self, queue, setup_users):
        """Test that idempotency keys return existing jobs."""
        user_id = setup_users
        
        # First enqueue
        job_id_1 = queue.enqueue(
            "test_job", user_id, idempotency_key="test-key-1"
        )
        
        # Second enqueue with same key
        job_id_2 = queue.enqueue(
            "test_job", user_id, idempotency_key="test-key-1"
        )
        
        # Should return the same job
        assert job_id_1 == job_id_2

    def test_enqueue_with_different_idempotency_creates_new_job(self, queue, setup_users):
        """Test that different idempotency keys create different jobs."""
        user_id = setup_users
        
        job_id_1 = queue.enqueue(
            "test_job", user_id, idempotency_key="test-key-1"
        )
        job_id_2 = queue.enqueue(
            "test_job", user_id, idempotency_key="test-key-2"
        )
        
        assert job_id_1 != job_id_2

    def test_enqueue_with_project(self, queue, setup_users, engine):
        """Test enqueueing a job with a project."""
        user_id = setup_users
        project_id = str(uuid4())
        
        # Create project in database
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO project_directory (id, relative_path, owner_user_id, created_at, updated_at)
                    VALUES (:id, :path, :owner, :created_at, :updated_at)
                    """
                ),
                {
                    "id": project_id,
                    "path": f"projects/{project_id}",
                    "owner": user_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )
        
        job_id = queue.enqueue("merge", user_id, project_id=project_id)
        
        job = queue.get_job(job_id)
        assert job.project_id == project_id


class TestJobQueueClaiming:
    """Test job claiming."""

    def test_claim_returns_queued_job(self, queue, setup_users):
        """Test that claim returns a queued job."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        
        claimed = queue.claim()
        
        assert claimed is not None
        assert claimed.id == job_id
        assert claimed.status == JobStatus.RUNNING
        assert claimed.lease_owner == queue.worker_id

    def test_claim_returns_none_when_empty(self, queue):
        """Test that claim returns None when queue is empty."""
        claimed = queue.claim()
        assert claimed is None

    def test_claim_is_atomic(self, queue, setup_users):
        """Test that claiming is atomic (only one worker gets a job)."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        
        # First worker claims
        claimed_1 = queue.claim()
        assert claimed_1 is not None
        assert claimed_1.id == job_id
        
        # Second worker tries to claim same job
        queue2 = JobQueue(queue.catalog_engine, worker_id="test-worker-2")
        claimed_2 = queue2.claim()
        
        # Should not get the same job
        assert claimed_2 is None

    def test_claim_respects_not_before(self, queue, setup_users, engine):
        """Test that claim doesn't return jobs with not_before in the future."""
        user_id = setup_users
        
        # Enqueue a job with not_before in the future
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        with engine.begin() as conn:
            job_id = str(uuid4())
            conn.execute(
                text(
                    """
                    INSERT INTO jobs (
                        id, project_id, user_id, type, status, priority,
                        not_before, attempt, max_attempts, created_at, updated_at
                    ) VALUES (
                        :id, :project_id, :user_id, :type, :status, :priority,
                        :not_before, :attempt, :max_attempts, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": job_id,
                    "project_id": None,
                    "user_id": user_id,
                    "type": "test_job",
                    "status": JobStatus.QUEUED.value,
                    "priority": 50,
                    "not_before": future_time,
                    "attempt": 1,
                    "max_attempts": 3,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            )
        
        # Should not claim this job
        claimed = queue.claim()
        assert claimed is None

    def test_claim_respects_priority(self, queue, setup_users):
        """Test that claim returns highest priority jobs first."""
        user_id = setup_users
        
        # Enqueue low priority job
        low_id = queue.enqueue("test_job", user_id, priority=10)
        
        # Enqueue high priority job
        high_id = queue.enqueue("test_job", user_id, priority=90)
        
        # Should claim high priority first
        claimed = queue.claim()
        assert claimed.id == high_id


class TestJobQueueLeaseRenewal:
    """Test lease heartbeat and renewal."""

    def test_renew_lease_extends_expiry(self, queue, setup_users):
        """Test that renewing a lease extends its expiry."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        
        claimed = queue.claim()
        original_expiry = claimed.lease_expires_at
        
        # Wait a bit and renew
        time.sleep(0.1)
        queue._renew_lease(job_id, queue.worker_id)
        
        # Check renewed job
        job = queue.get_job(job_id)
        assert job.lease_expires_at > original_expiry


class TestJobQueueReclaim:
    """Test lease expiry and reclaim."""

    def test_reclaim_expired_lease_moves_to_queued(self, queue, setup_users, engine):
        """Test that expired leases are reclaimed and moved back to queued."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id, max_attempts=3)
        
        # Claim the job
        claimed = queue.claim()
        assert claimed.status == JobStatus.RUNNING
        original_attempt = claimed.attempt
        
        # Manually expire the lease
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET lease_expires_at = :expires_at
                    WHERE id = :id
                    """
                ),
                {
                    "expires_at": now - timedelta(seconds=10),
                    "id": job_id,
                },
            )
        
        # Now claim again with a different worker
        # The second worker's claim() will reclaim the expired lease first
        queue2 = JobQueue(queue.catalog_engine, worker_id="test-worker-2")
        reclaimed = queue2.claim()
        
        # The reclaimed job should be the same job but with incremented attempt
        # and owned by the new worker
        assert reclaimed is not None
        assert reclaimed.id == job_id
        assert reclaimed.attempt == original_attempt + 1
        assert reclaimed.lease_owner == "test-worker-2"
        assert reclaimed.status == JobStatus.RUNNING

    def test_reclaim_max_attempts_moves_to_failed(self, queue, setup_users, engine):
        """Test that expired leases at max attempts are marked failed."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id, max_attempts=1)
        
        # Claim the job
        queue.claim()
        
        # Manually expire the lease
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE jobs SET lease_expires_at = :expires_at
                    WHERE id = :id
                    """
                ),
                {
                    "expires_at": now - timedelta(seconds=10),
                    "id": job_id,
                },
            )
        
        # Trigger reclaim
        queue2 = JobQueue(queue.catalog_engine, worker_id="test-worker-2")
        queue2.claim()
        
        # Should be marked failed
        job = queue.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error_code == "LEASE_EXPIRED"


class TestJobQueueCancellation:
    """Test job cancellation."""

    def test_cancel_queued_job_moves_to_cancelled(self, queue, setup_users):
        """Test cancelling a queued job moves it to cancelled."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        
        success = queue.cancel_job(job_id)
        
        assert success is True
        job = queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLED

    def test_cancel_running_job_moves_to_cancelling(self, queue, setup_users):
        """Test cancelling a running job moves it to cancelling."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        queue.claim()
        
        success = queue.cancel_job(job_id)
        
        assert success is True
        job = queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLING

    def test_cancel_idempotent(self, queue, setup_users):
        """Test that cancelling twice is idempotent."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        
        success1 = queue.cancel_job(job_id)
        assert success1 is True
        
        success2 = queue.cancel_job(job_id)
        assert success2 is False  # Already in terminal state

    def test_checkpoint_raises_when_job_cancelled(self, queue, setup_users):
        """Test that checkpoint raises JobCancelled when job is cancelled."""
        user_id = setup_users
        job_id = queue.enqueue("test_job", user_id)
        claimed = queue.claim()
        
        # Create a mock context
        with queue.catalog_engine.begin() as conn:
            from sqlalchemy.orm import Session
            session = Session(bind=queue.catalog_engine)
            temp_dir = Path(tempfile.gettempdir())
            
            ctx = JobContext(
                job=claimed,
                session=session,
                temp_dir=temp_dir,
                queue=queue,
                worker_id=queue.worker_id,
            )
            
            # Cancel the job
            queue.cancel_job(job_id)
            
            # Checkpoint should raise
            with pytest.raises(JobCancelled):
                ctx.checkpoint()
            
            session.close()
