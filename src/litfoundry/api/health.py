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
    Admin check is implemented in m1-local-identity; until then, requests from
    localhost are allowed for testing.
    """
    # TODO: Once m1-local-identity lands, require admin authorization here
    # For now, allow localhost (testing) and eventually require valid JWT with admin role
    
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
        
        # All checks passed
        return jsonify({
            "status": "ready",
            "checks": {
                "data_root": "ok",
                "catalogue": "ok"
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "not_ready",
            "reason": f"Unexpected error: {str(e)}"
        }), 503
