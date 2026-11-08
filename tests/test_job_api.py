"""Tests for job API endpoints (task 2.1)."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from litfoundry.app import create_app
from litfoundry.catalog import create_catalog_engine, run_alembic_upgrade, User
from litfoundry.jobs.queue import JobQueue
from litfoundry.jobs.types import JobStatus
from sqlalchemy.orm import sessionmaker
from flask_jwt_extended import create_access_token


class TestJobAPI:
    """Test job API endpoints."""

    @pytest.fixture
    def app_and_client(self):
        """Create test app and client."""
        tmpdir = tempfile.TemporaryDirectory()
        data_root = Path(tmpdir.name)
        
        # Set up catalog
        catalog_path = data_root / "catalog.sqlite"
        run_alembic_upgrade(catalog_path, target_revision="head")
        engine = create_catalog_engine(catalog_path)
        
        # Disable foreign key constraints for testing
        with engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("PRAGMA foreign_keys = OFF"))
        
        # Create app
        app = create_app({
            "TESTING": True,
            "DATA_ROOT": data_root,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        })
        
        # Re-configure app's engine
        from sqlalchemy.orm import scoped_session, sessionmaker as sm
        Session = sm(bind=engine)
        app.config["DB_SESSION_FACTORY"] = scoped_session(Session)
        app.config["job_queue"] = JobQueue(engine)
        
        client = app.test_client()
        
        yield app, client, engine, tmpdir
        
        engine.dispose()
        tmpdir.cleanup()

    def create_test_user(self, engine, username, role="editor"):
        """Create a test user."""
        Session = sessionmaker(bind=engine)
        session = Session()
        
        user = User(
            id=str(uuid4()),
            account_type="local",
            username=username,
            username_normalized=username.lower(),
            password_hash="dummy",
            must_change_password=False,
            role=role,
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

    def test_get_job_returns_200_for_requester(self, app_and_client):
        """Test GET /api/v1/jobs/{job_id} returns 200 for job requester."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user and job
        user_id = self.create_test_user(engine, "testuser")
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # Create JWT token
        with app.app_context():
            access_token = create_access_token(identity=user_id)
        
        # GET the job
        response = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == job_id
        assert data["status"] == JobStatus.QUEUED.value
        assert data["user_id"] == user_id

    def test_get_job_returns_404_for_unauthorized_user(self, app_and_client):
        """Test GET /api/v1/jobs/{job_id} returns 404 for unauthorized user."""
        app, client, engine, tmpdir = app_and_client
        
        # Create two users
        user_id = self.create_test_user(engine, "testuser1")
        other_user_id = self.create_test_user(engine, "testuser2")
        
        # Create job for first user
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # Try to access with other user
        with app.app_context():
            access_token = create_access_token(identity=other_user_id)
        
        response = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 404

    def test_get_job_returns_200_for_admin(self, app_and_client):
        """Test GET /api/v1/jobs/{job_id} returns 200 for admin."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user, admin, and job
        user_id = self.create_test_user(engine, "testuser")
        admin_id = self.create_test_user(engine, "admin", role="admin")
        
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # GET as admin
        with app.app_context():
            access_token = create_access_token(identity=admin_id)
        
        response = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == job_id

    def test_list_jobs_returns_user_jobs(self, app_and_client):
        """Test GET /api/v1/jobs returns user's jobs."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user and jobs
        user_id = self.create_test_user(engine, "testuser")
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        
        job_ids = []
        for i in range(3):
            job_id = queue.enqueue(
                user_id=user_id,
                project_id=project_id,
                job_type="test_job",
            )
            job_ids.append(job_id)
        
        # List jobs
        with app.app_context():
            access_token = create_access_token(identity=user_id)
        
        response = client.get(
            "/api/v1/jobs",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) == 3
        returned_ids = {job["id"] for job in data["jobs"]}
        assert returned_ids == set(job_ids)

    def test_list_jobs_admin_sees_all(self, app_and_client):
        """Test GET /api/v1/jobs for admin returns all jobs."""
        app, client, engine, tmpdir = app_and_client
        
        # Create two users
        user_id1 = self.create_test_user(engine, "testuser1")
        user_id2 = self.create_test_user(engine, "testuser2")
        admin_id = self.create_test_user(engine, "admin", role="admin")
        
        # Create jobs from both users
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        
        for user_id in [user_id1, user_id2]:
            for i in range(2):
                queue.enqueue(
                    user_id=user_id,
                    project_id=project_id,
                    job_type="test_job",
                )
        
        # List as admin
        with app.app_context():
            access_token = create_access_token(identity=admin_id)
        
        response = client.get(
            "/api/v1/jobs",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["jobs"]) == 4

    def test_cancel_job_moves_queued_to_cancelled(self, app_and_client):
        """Test POST /api/v1/jobs/{job_id}/cancel moves queued -> cancelled."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user and job
        user_id = self.create_test_user(engine, "testuser")
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # Cancel job
        with app.app_context():
            access_token = create_access_token(identity=user_id)
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 202
        data = response.get_json()
        assert data["job_id"] == job_id
        assert data["status"] == JobStatus.CANCELLED.value
        
        # Verify job is cancelled in database
        job = queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLED

    def test_cancel_job_moves_running_to_cancelling(self, app_and_client):
        """Test POST /api/v1/jobs/{job_id}/cancel moves running -> cancelling."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user and job
        user_id = self.create_test_user(engine, "testuser")
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # Claim the job (move to RUNNING)
        job = queue.claim()
        assert job is not None
        assert job.status == JobStatus.RUNNING
        
        # Cancel job
        with app.app_context():
            access_token = create_access_token(identity=user_id)
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 202
        data = response.get_json()
        assert data["job_id"] == job_id
        assert data["status"] == JobStatus.CANCELLING.value
        
        # Verify job is cancelling in database
        job = queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLING

    def test_cancel_job_is_idempotent(self, app_and_client):
        """Test POST /api/v1/jobs/{job_id}/cancel is idempotent."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user and job
        user_id = self.create_test_user(engine, "testuser")
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        with app.app_context():
            access_token = create_access_token(identity=user_id)
        
        # Cancel twice
        response1 = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response2 = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response1.status_code == 202
        assert response2.status_code == 202
        
        # Both should indicate cancelled status
        assert response1.get_json()["status"] == JobStatus.CANCELLED.value
        assert response2.get_json()["status"] == JobStatus.CANCELLED.value

    def test_cancel_job_forbidden_for_other_user(self, app_and_client):
        """Test POST /api/v1/jobs/{job_id}/cancel is forbidden for other user."""
        app, client, engine, tmpdir = app_and_client
        
        # Create two users
        user_id = self.create_test_user(engine, "testuser1")
        other_user_id = self.create_test_user(engine, "testuser2")
        
        # Create job for first user
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # Try to cancel as other user
        with app.app_context():
            access_token = create_access_token(identity=other_user_id)
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 403

    def test_cancel_job_allowed_for_admin(self, app_and_client):
        """Test POST /api/v1/jobs/{job_id}/cancel is allowed for admin."""
        app, client, engine, tmpdir = app_and_client
        
        # Create user and admin
        user_id = self.create_test_user(engine, "testuser")
        admin_id = self.create_test_user(engine, "admin", role="admin")
        
        # Create job for user
        queue = JobQueue(engine, "test-worker")
        project_id = str(uuid4())
        job_id = queue.enqueue(
            user_id=user_id,
            project_id=project_id,
            job_type="test_job",
        )
        
        # Cancel as admin
        with app.app_context():
            access_token = create_access_token(identity=admin_id)
        
        response = client.post(
            f"/api/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 202
        assert response.get_json()["status"] == JobStatus.CANCELLED.value
