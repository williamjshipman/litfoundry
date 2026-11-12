"""Background job endpoints."""

from datetime import datetime, timezone
from typing import Optional
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4

from litfoundry.jobs.queue import JobQueue
from litfoundry.jobs.types import JobStatus
from werkzeug.exceptions import Forbidden, NotFound
from sqlalchemy import text

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/v1/jobs")


def get_job_queue() -> JobQueue:
    """Get the job queue from Flask app context."""
    if "job_queue" not in current_app.config:
        # Lazy initialize the job queue
        from litfoundry.catalog import create_catalog_engine
        catalog_path = current_app.config["DATA_ROOT"] / "catalog.sqlite"
        engine = create_catalog_engine(catalog_path)
        current_app.config["job_queue"] = JobQueue(engine)
    return current_app.config["job_queue"]


def get_catalog_engine():
    """Get the catalog database engine."""
    if "catalog_engine" not in current_app.config:
        from litfoundry.catalog import create_catalog_engine
        catalog_path = current_app.config["DATA_ROOT"] / "catalog.sqlite"
        current_app.config["catalog_engine"] = create_catalog_engine(catalog_path)
    return current_app.config["catalog_engine"]


def accepted_response(job_id: str, status: str, status_url: str):
    """Return a 202 Accepted response for async operations."""
    return jsonify({
        "job_id": job_id,
        "status": status,
        "links": {
            "status": status_url,
        }
    }), 202


def get_user_role(user_id: str) -> str:
    """Get the user's role from the database."""
    engine = get_catalog_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT role FROM users WHERE id = :id"),
            {"id": user_id},
        )
        row = result.fetchone()
        return row[0] if row else "viewer"


def user_has_project_access(user_id: str, project_id: str, required_role: str = "viewer") -> bool:
    """Check if user has required access to project.
    
    Args:
        user_id: User ID
        project_id: Project ID
        required_role: Minimum required role (viewer or editor)
        
    Returns:
        True if user has access, False otherwise
    """
    engine = get_catalog_engine()
    
    with engine.connect() as conn:
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
        
        user_role = row[0]
        if required_role == "viewer":
            return user_role in ("viewer", "editor")
        elif required_role == "editor":
            return user_role == "editor"
        
        return False




@jobs_bp.route("", methods=["GET"])
@jwt_required()
def list_jobs():
    """Get the user's recent jobs or all jobs for admin.
    
    Returns:
        200 OK with list of jobs
    """
    user_id = get_jwt_identity()
    user_role = get_user_role(user_id)
    queue = get_job_queue()
    
    # Admin sees all jobs, others see only their own
    if user_role == "admin":
        jobs = queue.list_jobs(limit=50)
    else:
        jobs = queue.list_jobs(user_id=user_id, limit=50)
    
    # Convert to JSON-serializable dicts
    job_dicts = []
    for job in jobs:
        job_dicts.append({
            "id": job.id,
            "type": job.type,
            "status": job.status.value,
            "user_id": job.user_id,
            "project_id": job.project_id,
            "progress": job.progress_json,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "error_cause": job.error_cause,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        })
    
    return jsonify({
        "jobs": job_dicts
    }), 200


@jobs_bp.route("/<job_id>", methods=["GET"])
@jwt_required()
def get_job(job_id: str):
    """Get a single job's status and progress.
    
    Access: Own job, users with read access to project, or admin.
    
    Args:
        job_id: Job ID
        
    Returns:
        200 OK with job details
        404 Not Found if job not accessible
    """
    user_id = get_jwt_identity()
    user_role = get_user_role(user_id)
    queue = get_job_queue()
    
    job = queue.get_job(job_id)
    if not job:
        raise NotFound({"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
    
    # Check access: requester, project access, or admin
    is_owner = user_id == job.user_id
    is_admin = user_role == "admin"
    has_project_access = False
    
    if job.project_id:
        has_project_access = user_has_project_access(user_id, job.project_id, "viewer")
    
    if not (is_owner or is_admin or has_project_access):
        raise NotFound({"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
    
    return jsonify({
        "id": job.id,
        "type": job.type,
        "status": job.status.value,
        "user_id": job.user_id,
        "project_id": job.project_id,
        "progress": job.progress_json,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "error_cause": job.error_cause,
        "attempt": job.attempt,
        "max_attempts": job.max_attempts,
        "correlation_id": job.correlation_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }), 200




@jobs_bp.route("/queue/health", methods=["GET"])
@jwt_required()
def get_queue_health():
    """Get job queue health statistics (admin only).
    
    Returns:
        200 OK with queue health data
        403 Forbidden if not admin
    """
    user_id = get_jwt_identity()
    user_role = get_user_role(user_id)
    
    if user_role != "admin":
        raise Forbidden({"error_code": "FORBIDDEN", "message": "Admin access required"})
    
    queue = get_job_queue()
    health = queue.get_queue_health()
    
    return jsonify(health), 200



