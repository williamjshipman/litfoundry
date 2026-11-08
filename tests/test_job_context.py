"""Tests for JobContext and job execution."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import time
import json

import pytest
from sqlalchemy import text

from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade
from litfoundry.jobs import (
    JobQueue, JobStatus, JobProgress, JobResult, JobContext,
    RetryableError, NonRetryableError, JobCancelled
)
from litfoundry.jobs.handlers import get_test_job_handler


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
    queue = JobQueue(engine, worker_id="test-worker-1")
    queue.register_handler("test", get_test_job_handler())
    return queue


@pytest.fixture
def setup_users(engine):
    """Create test users in the database."""
    now = datetime.now(timezone.utc)
    
    with engine.begin() as conn:
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


class TestJobContextCheckpoint:
    """Test JobContext checkpoint functionality."""

    def test_checkpoint_checks_cancellation(self, queue, setup_users):
        """Test that checkpoint checks for cancellation."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from sqlalchemy.orm import Session
            session = Session(bind=queue.catalog_engine)
            temp_dir = Path(tmpdir)
            
            ctx = JobContext(
                job=claimed,
                session=session,
                temp_dir=temp_dir,
                queue=queue,
                worker_id=queue.worker_id,
            )
            
            # First checkpoint should succeed
            ctx.checkpoint()
            
            # Cancel the job
            queue.cancel_job(job_id)
            
            # Next checkpoint should raise JobCancelled
            with pytest.raises(JobCancelled):
                ctx.checkpoint()
            
            session.close()

    def test_checkpoint_renews_lease(self, queue, setup_users):
        """Test that checkpoint renews the lease."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)
        claimed = queue.claim()
        original_expiry = claimed.lease_expires_at
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from sqlalchemy.orm import Session
            session = Session(bind=queue.catalog_engine)
            temp_dir = Path(tmpdir)
            
            ctx = JobContext(
                job=claimed,
                session=session,
                temp_dir=temp_dir,
                queue=queue,
                worker_id=queue.worker_id,
            )
            
            # Force a checkpoint to renew the lease (by setting the last_heartbeat far back)
            ctx._last_heartbeat = time.time() - 15  # Force immediate renewal
            
            # Checkpoint should renew the lease
            ctx.checkpoint()
            
            # Check the renewed job
            job = queue.get_job(job_id)
            assert job.lease_expires_at > original_expiry
            
            session.close()


class TestJobContextProgress:
    """Test JobContext progress reporting."""

    def test_progress_updates_job(self, queue, setup_users):
        """Test that progress updates are stored."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from sqlalchemy.orm import Session
            session = Session(bind=queue.catalog_engine)
            temp_dir = Path(tmpdir)
            
            ctx = JobContext(
                job=claimed,
                session=session,
                temp_dir=temp_dir,
                queue=queue,
                worker_id=queue.worker_id,
            )
            
            # Report progress
            progress = JobProgress(
                message="Processing",
                percent_complete=50.0,
            )
            ctx.progress(progress)
            
            # Check the job's progress_json was updated
            job = queue.get_job(job_id)
            assert job.progress_json is not None
            
            progress_data = json.loads(job.progress_json)
            assert progress_data["message"] == "Processing"
            assert progress_data["percent_complete"] == 50.0
            
            session.close()


class TestJobExecution:
    """Test job execution."""

    def test_execute_successful_job(self, queue, setup_users, engine):
        """Test executing a successful job."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            queue.execute_job(claimed, temp_dir)
        
        # Check the job is marked completed
        job = queue.get_job(job_id)
        assert job.status == JobStatus.COMPLETED
        assert job.lease_owner is None
        assert job.completed_at is not None

    def test_execute_job_with_retryable_error(self, queue, setup_users, engine):
        """Test executing a job that fails with a retryable error."""
        user_id = setup_users
        
        # Enqueue with should_fail and retryable mode
        progress_json = json.dumps({
            "should_fail": True,
            "failure_mode": "retryable",
            "items": 1,
        })
        
        job_id = queue.enqueue("test", user_id, max_attempts=3)
        
        # Update progress_json to trigger failure
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE jobs SET progress_json = :progress WHERE id = :id"),
                {"progress": progress_json, "id": job_id},
            )
        
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            queue.execute_job(claimed, temp_dir)
        
        # Check the job is back in queued state (will be retried)
        job = queue.get_job(job_id)
        assert job.status == JobStatus.QUEUED
        assert job.attempt == 2
        assert job.error_code == "TEMPORARY_ERROR"

    def test_execute_job_with_non_retryable_error(self, queue, setup_users, engine):
        """Test executing a job that fails with a non-retryable error."""
        user_id = setup_users
        
        # Enqueue with should_fail and non-retryable mode
        progress_json = json.dumps({
            "should_fail": True,
            "failure_mode": "non_retryable",
            "items": 1,
        })
        
        job_id = queue.enqueue("test", user_id, max_attempts=3)
        
        # Update progress_json to trigger failure
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE jobs SET progress_json = :progress WHERE id = :id"),
                {"progress": progress_json, "id": job_id},
            )
        
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            queue.execute_job(claimed, temp_dir)
        
        # Check the job is marked failed
        job = queue.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error_code == "JOB_FAILED"  # Spec: failed jobs report JOB_FAILED
        assert job.error_cause == "SIMULATED_ERROR"  # Typed cause is preserved

    def test_execute_cancelled_job(self, queue, setup_users):
        """Test that a job cancelled at checkpoint stops cleanly."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)
        claimed = queue.claim()
        
        # Cancel immediately (will be detected at first checkpoint)
        queue.cancel_job(job_id)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            queue.execute_job(claimed, temp_dir)
        
        # Check the job is marked cancelled
        job = queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLED
        assert job.lease_owner is None

    def test_execute_job_without_handler(self, queue, setup_users):
        """Test executing a job with no registered handler."""
        user_id = setup_users
        job_id = queue.enqueue("unknown_type", user_id)
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            queue.execute_job(claimed, temp_dir)
        
        # Check the job is marked failed
        job = queue.get_job(job_id)
        assert job.status == JobStatus.FAILED
        assert job.error_code == "JOB_FAILED"
        assert "No handler" in job.error_message

    def test_handler_registration(self, queue):
        """Test registering and looking up handlers."""
        def my_handler(ctx):
            return JobResult(status=JobStatus.COMPLETED)
        
        queue.register_handler("my_type", my_handler)
        
        assert "my_type" in queue._job_handlers
        assert queue._job_handlers["my_type"] == my_handler


class TestJobContextTempDir:
    """Test job context temp directory."""

    def test_temp_dir_provided(self, queue, setup_users):
        """Test that temp directory is provided to job context."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from sqlalchemy.orm import Session
            session = Session(bind=queue.catalog_engine)
            temp_dir = Path(tmpdir)
            
            ctx = JobContext(
                job=claimed,
                session=session,
                temp_dir=temp_dir,
                queue=queue,
                worker_id=queue.worker_id,
            )
            
            # Verify temp_dir exists and is accessible
            assert ctx.temp_dir.exists()
            assert ctx.temp_dir.is_dir()
            
            # Verify we can write to it
            test_file = ctx.temp_dir / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists()
            assert test_file.read_text() == "test content"
            
            session.close()


class TestJobContextAuthorization:
    """Test job context authorization checks."""

    def test_authorize_system_job(self, queue, setup_users):
        """Test that system jobs (no project) always authorize."""
        user_id = setup_users
        job_id = queue.enqueue("test", user_id)  # No project_id
        claimed = queue.claim()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from sqlalchemy.orm import Session
            session = Session(bind=queue.catalog_engine)
            temp_dir = Path(tmpdir)
            
            ctx = JobContext(
                job=claimed,
                session=session,
                temp_dir=temp_dir,
                queue=queue,
                worker_id=queue.worker_id,
            )
            
            # Should always authorize for system jobs
            assert ctx.authorize("viewer") is True
            assert ctx.authorize("editor") is True
            
            session.close()
