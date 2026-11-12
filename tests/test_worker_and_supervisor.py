"""Tests for background job worker and supervisor."""

import tempfile
from pathlib import Path

import pytest

from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade
from litfoundry.jobs.types import JobStatus
from litfoundry.jobs.queue import JobQueue


class TestWorkerAndSupervisor:
    """Test the background job worker and supervisor commands."""

    def test_worker_cli_command_exists(self):
        """Test that the worker CLI command exists and shows help."""
        import subprocess
        import sys
        
        result = subprocess.run(
            [sys.executable, "-m", "litfoundry.cli", "worker", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "worker" in result.stdout.lower()
        assert "background job" in result.stdout.lower()

    def test_supervise_cli_command_exists(self):
        """Test that the supervise CLI command exists and shows help."""
        import subprocess
        import sys
        
        result = subprocess.run(
            [sys.executable, "-m", "litfoundry.cli", "supervise", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "supervise" in result.stdout.lower()
        assert "supervisor" in result.stdout.lower()

    def test_job_queue_basic_workflow(self):
        """Test basic job queue workflow (enqueue, claim, execute)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.sqlite"
            
            # Set up catalog
            run_alembic_upgrade(catalog_path, target_revision="head")
            engine = create_catalog_engine(catalog_path)
            
            try:
                # Create a test user directly with ORM
                from litfoundry.catalog import User
                from datetime import datetime, timezone
                from uuid import uuid4
                from sqlalchemy.orm import sessionmaker
                
                Session = sessionmaker(bind=engine)
                session = Session()
                
                user = User(
                    id=str(uuid4()),
                    account_type="local",
                    username="testuser",
                    username_normalized="testuser",
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
                
                # Enqueue a test job
                queue = JobQueue(engine)
                from litfoundry.jobs.handlers import create_test_job_handler
                queue.register_handler("test", create_test_job_handler())
                
                job_id = queue.enqueue(
                    job_type="test",
                    user_id=user_id,
                    max_attempts=1,
                )
                
                # Claim the job
                job = queue.claim()
                assert job is not None
                assert job.id == job_id
                assert job.status == JobStatus.RUNNING.value
                
                # Execute the job
                temp_dir = Path(tmpdir) / "job_temp"
                temp_dir.mkdir(exist_ok=True)
                queue.execute_job(job, temp_dir)
                
                # Verify job completed
                final_job = queue.get_job(job_id)
                assert final_job.status == JobStatus.COMPLETED.value
            finally:
                engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

