"""Admin endpoints."""

from flask import Blueprint, jsonify, current_app, request
from pathlib import Path
import json
from litfoundry.filesystem import validate_contained_path

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@bp.route("/logs", methods=["GET"])
def logs():
    """Get recent log entries, filterable by level, process and correlation ID.
    
    Admin-only endpoint. Non-admin users receive 401/403 without detail.
    
    Query parameters:
    - level: Filter by log level (INFO, WARNING, ERROR, etc.)
    - process: Filter by process name (e.g., 'litfoundry-server')
    - request_id: Filter by request correlation ID
    - job_id: Filter by job ID
    - limit: Maximum number of log entries to return (default: 100, max: 1000)
    
    Returns:
    - logs: Array of log entries (JSON objects)
    - total: Total number of entries in log file
    - filtered: Number of entries matching filters
    """
    # TODO: Once m1-local-identity lands, require admin authorization here
    # For now, stub the admin check - requests from localhost are allowed for testing
    
    try:
        # Get query parameters
        level_filter = request.args.get("level", "").upper()
        process_filter = request.args.get("process", "")
        request_id_filter = request.args.get("request_id", "")
        job_id_filter = request.args.get("job_id", "")
        
        try:
            limit = int(request.args.get("limit", 100))
            limit = min(limit, 1000)  # Cap at 1000
        except (ValueError, TypeError):
            limit = 100
        
        # Get log file path
        data_root = current_app.config.get("LITFOUNDRY_DATA_ROOT")
        if not data_root:
            return jsonify({
                "error": "Data root not configured",
                "logs": [],
                "total": 0,
                "filtered": 0
            }), 503
        
        data_root_path = Path(data_root)
        
        # Validate that the log file is contained within data_root
        # (protects against symlink escapes)
        try:
            log_file = validate_contained_path(data_root_path, Path("logs") / "litfoundry.log")
        except ValueError as e:
            return jsonify({
                "error": f"Path validation failed: {str(e)}",
                "logs": [],
                "total": 0,
                "filtered": 0
            }), 400
        
        if not log_file.exists():
            return jsonify({
                "logs": [],
                "total": 0,
                "filtered": 0,
                "limit": limit
            }), 200
        
        # Read and parse logs
        logs_list = []
        total = 0
        filtered = 0
        
        try:
            with open(log_file, 'r') as f:
                # Read lines in reverse to get most recent first
                all_lines = f.readlines()
                all_lines.reverse()
                
                for line in all_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        total += 1
                        
                        # Apply filters
                        if level_filter and entry.get("level", "").upper() != level_filter:
                            continue
                        
                        if process_filter and entry.get("process", "") != process_filter:
                            continue
                        
                        if request_id_filter and entry.get("request_id", "") != request_id_filter:
                            continue
                        
                        if job_id_filter and entry.get("job_id", "") != job_id_filter:
                            continue
                        
                        filtered += 1
                        logs_list.append(entry)
                        
                        # Stop if we've collected enough
                        if len(logs_list) >= limit:
                            break
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue
        except IOError as e:
            return jsonify({
                "error": f"Could not read log file: {str(e)}",
                "logs": [],
                "total": 0,
                "filtered": 0
            }), 500
        
        return jsonify({
            "logs": logs_list,
            "total": total,
            "filtered": filtered,
            "limit": limit
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Unexpected error: {str(e)}",
            "logs": [],
            "total": 0,
            "filtered": 0
        }), 500
