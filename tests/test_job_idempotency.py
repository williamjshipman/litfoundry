"""Tests for job idempotency."""

import tempfile
from pathlib import Path

import pytest

from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade
from litfoundry.jobs.queue import JobQueue


class TestJobIdempotency:
    """Test job idempotency keys for double-submit prevention."""

    def test_double_submit_returns_same_job_id(self):
        """Test that submitting the same job twice returns the same job ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.sqlite"
            
            # Set up catalog
            run_alembic_upgrade(catalog_path, target_revision="head")
            engine = create_catalog_engine(catalog_path)
            
            try:
                # Create a test user
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
                
                # Create queue
                queue = JobQueue(engine)
                
                # Submit job with idempotency key
                idempotency_key = "test-import-123"
                job_id_1 = queue.enqueue(
                    job_type="import",
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                )
                
                # Submit again with same idempotency key
                job_id_2 = queue.enqueue(
                    job_type="import",
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                )
                
                # Should return the same job ID
                assert job_id_1 == job_id_2, "Idempotency key did not prevent duplicate job creation"
                
                # Verify there's only one job in the database
                with engine.connect() as conn:
                    from sqlalchemy import text
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM jobs WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    count = result.scalar()
                    assert count == 1, f"Expected 1 job but found {count}"
            finally:
                engine.dispose()

    def test_different_idempotency_keys_create_different_jobs(self):
        """Test that different idempotency keys create separate jobs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.sqlite"
            
            # Set up catalog
            run_alembic_upgrade(catalog_path, target_revision="head")
            engine = create_catalog_engine(catalog_path)
            
            try:
                # Create a test user
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
                
                # Create queue
                queue = JobQueue(engine)
                
                # Submit job with first idempotency key
                job_id_1 = queue.enqueue(
                    job_type="import",
                    user_id=user_id,
                    idempotency_key="import-key-1",
                )
                
                # Submit with different idempotency key
                job_id_2 = queue.enqueue(
                    job_type="import",
                    user_id=user_id,
                    idempotency_key="import-key-2",
                )
                
                # Should create separate jobs
                assert job_id_1 != job_id_2, "Different idempotency keys should create different jobs"
                
                # Verify there are two jobs
                with engine.connect() as conn:
                    from sqlalchemy import text
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM jobs WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    count = result.scalar()
                    assert count == 2, f"Expected 2 jobs but found {count}"
            finally:
                engine.dispose()

    def test_idempotency_key_null_allows_duplicates(self):
        """Test that jobs without idempotency keys can be submitted multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = Path(tmpdir) / "catalog.sqlite"
            
            # Set up catalog
            run_alembic_upgrade(catalog_path, target_revision="head")
            engine = create_catalog_engine(catalog_path)
            
            try:
                # Create a test user
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
                
                # Create queue
                queue = JobQueue(engine)
                
                # Submit job without idempotency key
                job_id_1 = queue.enqueue(
                    job_type="import",
                    user_id=user_id,
                )
                
                # Submit again without idempotency key
                job_id_2 = queue.enqueue(
                    job_type="import",
                    user_id=user_id,
                )
                
                # Should create separate jobs (no idempotency without key)
                assert job_id_1 != job_id_2
                
                # Verify there are two jobs
                with engine.connect() as conn:
                    from sqlalchemy import text
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM jobs WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    count = result.scalar()
                    assert count == 2, f"Expected 2 jobs but found {count}"
            finally:
                engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
