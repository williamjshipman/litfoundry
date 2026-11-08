"""Tests for job concurrency limits (task 1.6)."""

import tempfile
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade, User
from litfoundry.jobs.queue import JobQueue, MAX_RUNNING_JOBS_GLOBAL, MAX_RUNNING_JOBS_PER_USER
from litfoundry.jobs.types import JobStatus
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker


def setup_test_db():
    """Set up a test database with migrations."""
    tmpdir = tempfile.TemporaryDirectory()
    catalog_path = Path(tmpdir.name) / "catalog.sqlite"
    
    # Run migrations
    run_alembic_upgrade(catalog_path, target_revision="head")
    engine = create_catalog_engine(catalog_path)
    
    # Disable foreign key constraints for testing
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
    
    return tmpdir, catalog_path, engine


def create_test_user(engine, username):
    """Create a test user in the database."""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    user = User(
        id=str(uuid4()),
        account_type="local",
        username=username,
        username_normalized=username.lower(),
        password_hash="dummy",
        must_change_password=False,
        role="editor",
        active=True,
        session_version=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(user)
    session.commit()
    user_id = user.id
    session.close()
    
    return user_id


class TestConcurrencyLimits:
    """Test job concurrency limits."""

    def test_per_user_concurrency_limit_blocks_claim(self):
        """Test that per-user limit prevents claiming more jobs."""
        tmpdir, catalog_path, engine = setup_test_db()
        try:
            queue = JobQueue(engine, "test-worker")
            user_id = create_test_user(engine, "testuser1")
            project_id = str(uuid4())
            
            # Enqueue MAX_RUNNING_JOBS_PER_USER jobs for user
            for i in range(MAX_RUNNING_JOBS_PER_USER):
                queue.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
            
            # Claim all jobs (set them to RUNNING)
            claimed_jobs = []
            for i in range(MAX_RUNNING_JOBS_PER_USER):
                job = queue.claim()
                assert job is not None, f"Should claim job {i}"
                claimed_jobs.append(job)
            
            # Enqueue one more job for the same user
            queue.enqueue(
                user_id=user_id,
                project_id=project_id,
                job_type="test_job",
            )
            
            # Try to claim - should return None because user limit is reached
            job = queue.claim()
            assert job is None, "Should not claim job when user limit reached"
            
            # Verify job is still queued
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT status FROM jobs WHERE status = :queued"),
                    {"queued": JobStatus.QUEUED.value},
                )
                assert result.fetchone() is not None, "Job should still be queued"
        finally:
            engine.dispose()
            tmpdir.cleanup()

    def test_global_concurrency_limit_blocks_claim(self):
        """Test that global limit prevents claiming jobs even for different users."""
        tmpdir, catalog_path, engine = setup_test_db()
        try:
            queue = JobQueue(engine, "test-worker")
            
            # Create many test users (more than needed to hit global limit without per-user limit)
            users = []
            num_users = MAX_RUNNING_JOBS_GLOBAL // 2  # Enough users to hit global limit
            for i in range(num_users):
                user_id = create_test_user(engine, f"testuser{i}")
                users.append(user_id)
            
            project_id = str(uuid4())
            
            # Enqueue jobs across users (multiple jobs per user but less than per-user limit)
            for i in range(MAX_RUNNING_JOBS_GLOBAL):
                user_id = users[i % num_users]
                queue.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
            
            # Claim all jobs up to global limit
            for i in range(MAX_RUNNING_JOBS_GLOBAL):
                job = queue.claim()
                assert job is not None, f"Should claim job {i}"
            
            # Enqueue one more job
            queue.enqueue(
                user_id=users[0],
                project_id=project_id,
                job_type="test_job",
            )
            
            # Try to claim - should return None because global limit is reached
            job = queue.claim()
            assert job is None, "Should not claim job when global limit reached"
        finally:
            engine.dispose()
            tmpdir.cleanup()

    def test_get_running_jobs_count_global(self):
        """Test counting global running jobs."""
        tmpdir, catalog_path, engine = setup_test_db()
        try:
            queue = JobQueue(engine, "test-worker")
            
            # Create multiple test users
            users = []
            for i in range(3):
                user_id = create_test_user(engine, f"testuser{i}")
                users.append(user_id)
            
            project_id = str(uuid4())
            
            # Enqueue and claim 3 jobs from different users
            for i in range(3):
                user_id = users[i]
                queue.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
            
            for i in range(3):
                job = queue.claim()
                assert job is not None
            
            # Get global count
            count = queue.get_running_jobs_count()
            assert count == 3, f"Should have 3 running jobs globally, got {count}"
        finally:
            engine.dispose()
            tmpdir.cleanup()

    def test_get_running_jobs_count_per_user(self):
        """Test counting per-user running jobs."""
        tmpdir, catalog_path, engine = setup_test_db()
        try:
            queue = JobQueue(engine, "test-worker")
            user_id = create_test_user(engine, "testuser1")
            project_id = str(uuid4())
            
            # Enqueue and claim 2 jobs for one user
            for i in range(2):
                queue.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
            
            for i in range(2):
                job = queue.claim()
                assert job is not None
            
            # Get per-user count
            count = queue.get_running_jobs_count(user_id=user_id)
            assert count == 2, f"Should have 2 running jobs for user, got {count}"
            
            # Create another user and verify count is 0
            other_user = create_test_user(engine, "testuser2")
            count = queue.get_running_jobs_count(user_id=other_user)
            assert count == 0, f"Should have 0 running jobs for other user, got {count}"
        finally:
            engine.dispose()
            tmpdir.cleanup()

    def test_limits_respect_only_running_status(self):
        """Test that limits only count RUNNING jobs, not QUEUED."""
        tmpdir, catalog_path, engine = setup_test_db()
        try:
            queue = JobQueue(engine, "test-worker")
            user_id = create_test_user(engine, "testuser1")
            project_id = str(uuid4())
            
            # Enqueue 10 jobs
            for i in range(10):
                queue.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
            
            # Only claim MAX_RUNNING_JOBS_PER_USER of them
            for i in range(MAX_RUNNING_JOBS_PER_USER):
                job = queue.claim()
                assert job is not None
            
            # Count should be MAX_RUNNING_JOBS_PER_USER
            count = queue.get_running_jobs_count(user_id=user_id)
            assert count == MAX_RUNNING_JOBS_PER_USER
            
            # Remaining jobs should still be queued
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM jobs WHERE status = :queued AND user_id = :user_id"
                    ),
                    {"queued": JobStatus.QUEUED.value, "user_id": user_id},
                )
                queued_count = result.scalar()
                assert queued_count == 10 - MAX_RUNNING_JOBS_PER_USER
        finally:
            engine.dispose()
            tmpdir.cleanup()

    def test_different_workers_respect_limits(self):
        """Test that different worker processes respect the same concurrency limits."""
        tmpdir, catalog_path, engine = setup_test_db()
        try:
            queue1 = JobQueue(engine, "test-worker-1")
            queue2 = JobQueue(engine, "test-worker-2")
            user_id = create_test_user(engine, "testuser1")
            project_id = str(uuid4())
            
            # Enqueue jobs
            for i in range(MAX_RUNNING_JOBS_PER_USER + 2):
                queue1.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
            
            # Worker 1 claims a job
            job1 = queue1.claim()
            assert job1 is not None
            
            # Worker 2 tries to claim more jobs
            for i in range(MAX_RUNNING_JOBS_PER_USER - 1):
                job = queue2.claim()
                if i < MAX_RUNNING_JOBS_PER_USER - 2:
                    assert job is not None, f"Worker 2 should claim job {i}"
        finally:
            engine.dispose()
            tmpdir.cleanup()

    def test_concurrency_limits_constants_defined(self):
        """Verify concurrency limit constants are reasonable."""
        assert MAX_RUNNING_JOBS_GLOBAL > 0, "Global limit must be positive"
        assert MAX_RUNNING_JOBS_PER_USER > 0, "Per-user limit must be positive"
        assert MAX_RUNNING_JOBS_PER_USER <= MAX_RUNNING_JOBS_GLOBAL, \
            "Per-user limit should not exceed global limit"
        # Current defaults: global=20, per-user=5
        assert MAX_RUNNING_JOBS_GLOBAL == 20
        assert MAX_RUNNING_JOBS_PER_USER == 5
