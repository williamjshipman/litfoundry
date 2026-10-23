"""Health check endpoints."""

from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/api/v1/health")


@bp.route("/live", methods=["GET"])
def live():
    """Liveness probe endpoint."""
    return jsonify({"status": "alive"}), 200


@bp.route("/ready", methods=["GET"])
def ready():
    """Readiness probe endpoint. Admin-only."""
    # TODO: Check admin authorization when identity is implemented
    return jsonify({"status": "ready"}), 200
