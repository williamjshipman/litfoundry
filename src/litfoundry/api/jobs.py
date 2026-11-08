"""Background job endpoints."""

from datetime import datetime, timezone
from typing import Optional
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from uuid import uuid4

from litfoundry.jobs.queue import JobQueue
from litfoundry.jobs.types import JobStatus
from werkzeug.exceptions import Forbidden, NotFound

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
    from litfoundry.catalog import User
    session = current_app.config.get("DB_SESSION_FACTORY")
    if not session:
        return "viewer"  # Default if session not available
    
    user = session.query(User).filter_by(id=user_id).first()
    return user.role if user else "viewer"


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
    if user_id != job.user_id and user_role != "admin":
        # Check if user has access to the project (if not system job)
        if job.project_id:
            # Check project ACL
            from litfoundry.catalog import User, project_acl
            session = current_app.config.get("DB_SESSION_FACTORY")
            if session:
                acl = session.query(project_acl).filter_by(
                    project_id=job.project_id,
                    user_id=user_id
                ).first()
                if not acl:
                    raise NotFound({"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
            else:
                raise NotFound({"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
        else:
            # System job without project access
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


@jobs_bp.route("/<job_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_job(job_id: str):
    """Cancel a job (idempotent).
    
    Args:
        job_id: Job ID
        
    Returns:
        202 Accepted with updated job status
        404 Not Found if job not accessible
    """
    user_id = get_jwt_identity()
    user_role = get_user_role(user_id)
    queue = get_job_queue()
    
    job = queue.get_job(job_id)
    if not job:
        raise NotFound({"error_code": "JOB_NOT_FOUND", "message": "Job not found"})
    
    # Check access: requester or admin
    if user_id != job.user_id and user_role != "admin":
        raise Forbidden({"error_code": "FORBIDDEN", "message": "Cannot cancel this job"})
    
    # Cancel the job
    queue.cancel_job(job_id)
    
    # Get updated job
    job = queue.get_job(job_id)
    
    status_url = f"/api/v1/jobs/{job_id}"
    return accepted_response(job_id, job.status.value, status_url)

