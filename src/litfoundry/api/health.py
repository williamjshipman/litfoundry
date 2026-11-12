"""Health check endpoints."""

from flask import Blueprint, jsonify, current_app
import os

bp = Blueprint("health", __name__, url_prefix="/api/v1/health")


@bp.route("/live", methods=["GET"])
def live():
    """Liveness probe endpoint.
    
    Always returns 200 if the application is running.
    Used by orchestrators (Kubernetes, Docker, etc.) to detect if the process is alive.
    """
    return jsonify({"status": "alive"}), 200


@bp.route("/ready", methods=["GET"])
def ready():
    """Readiness probe endpoint. Admin-only.
    
    Returns 200 if the application is ready to serve requests.
    Checks include:
    - Catalogue database is accessible
    - Data root is initialized
    - Configuration is valid
    
    This endpoint requires admin privileges. Unauthenticated requests return 401.
    """
    # Require admin authorization
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    from litfoundry.api.errors import ApiError
    from sqlalchemy.orm import scoped_session
    from litfoundry.catalog import User
    
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            if not user or user.role != "admin" or not user.active:
                raise ApiError(
                    code="FORBIDDEN",
                    status=403,
                    message="Admin access required"
                )
        finally:
            db_session.remove()
    except Exception as e:
        if isinstance(e, ApiError):
            raise
        raise ApiError(
            code="FORBIDDEN",
            status=403,
            message="Admin access required"
        )
    
    try:
        # Check data root is set and accessible
        data_root = current_app.config.get("LITFOUNDRY_DATA_ROOT")
        if not data_root:
            return jsonify({
                "status": "not_ready",
                "reason": "Data root not configured"
            }), 503
        
        data_root_path = os.path.expandvars(str(data_root))
        if not os.path.isdir(data_root_path):
            return jsonify({
                "status": "not_ready",
                "reason": "Data root not found or not accessible"
            }), 503
        
        # Check catalogue database exists
        catalogue_db = os.path.join(data_root_path, "catalog.sqlite")
        if not os.path.isfile(catalogue_db):
            return jsonify({
                "status": "not_ready",
                "reason": "Catalogue database not initialized"
            }), 503
        
        # Check initialization marker file
        initialized_marker = os.path.join(data_root_path, ".initialized")
        if not os.path.isfile(initialized_marker):
            return jsonify({
                "status": "not_ready",
                "reason": "Data root not fully initialized"
            }), 503
        
        # Verify catalogue database is readable and has required schema
        try:
            import sqlite3
            conn = sqlite3.connect(f"file:{catalogue_db}?mode=ro", uri=True, timeout=1)
            
            # Check that schema_meta table exists (indicates migrations have been applied)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'"
            )
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    "status": "not_ready",
                    "reason": "Catalogue schema not initialized (missing schema_meta table)"
                }), 503
            
            # Check that system_settings table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'"
            )
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    "status": "not_ready",
                    "reason": "Catalogue schema incomplete (missing system_settings table)"
                }), 503
            
            conn.close()
        except Exception as e:
            return jsonify({
                "status": "not_ready",
                "reason": f"Catalogue database error: {str(e)}"
            }), 503
        
        # Check job queue health
        job_queue = current_app.config.get("job_queue")
        if job_queue:
            health = job_queue.get_queue_health()
            # Check if we have workers with active heartbeats
            active_workers = [w for w in health.get("worker_heartbeats", []) if w["status"] == "active"]
            if not active_workers and health.get("running_count", 0) > 0:
                # Jobs are running but no active workers detected
                return jsonify({
                    "status": "not_ready",
                    "reason": "Job workers not responding"
                }), 503
        
        # All checks passed
        return jsonify({
            "status": "ready",
            "checks": {
                "data_root": "ok",
                "catalogue": "ok",
                "job_queue": "ok" if not job_queue or len([w for w in job_queue.get_queue_health().get("worker_heartbeats", []) if w["status"] == "active"]) > 0 else "stale"
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "not_ready",
            "reason": f"Unexpected error: {str(e)}"
        }), 503
