"""Admin endpoints."""

from flask import Blueprint, jsonify

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@bp.route("/logs", methods=["GET"])
def logs():
    """Get system logs. Admin-only."""
    # TODO: Implement log retrieval when identity is implemented
    return jsonify({"logs": []}), 200
