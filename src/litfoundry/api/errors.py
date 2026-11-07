"""API error handling and standard error codes."""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from flask import current_app, jsonify, request, Response
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


# Error code registry with fixed HTTP statuses
ERROR_CODES = {
    "VALIDATION_ERROR": 400,
    "UNAUTHENTICATED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "RECORD_LOCKED": 409,
    "PROJECT_BUSY": 409,
    "QUOTA_EXCEEDED": 409,
    "PAYLOAD_TOO_LARGE": 413,
    "MAINTENANCE_IN_PROGRESS": 503,
    "INTERNAL_ERROR": 500,
}


@dataclass
class ApiError(Exception):
    """Structured API error with code, status, message and optional details."""

    code: str
    status: int
    message: str
    details: Optional[dict[str, Any]] = None

    def __init__(
        self,
        code: str,
        status: int,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.code = code
        self.status = status
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self, request_id: str) -> dict[str, Any]:
        """Convert to JSON-serializable dict with request_id."""
        result = {
            "code": self.code,
            "message": self.message,
            "request_id": request_id,
        }
        if self.details:
            result["details"] = self.details
        return result


def get_or_create_request_id() -> str:
    """Get or create a unique request ID for this request."""
    if not hasattr(request, "request_id"):
        request.request_id = str(uuid.uuid4())
    return request.request_id


def handle_api_error(error: ApiError) -> Response:
    """Handle an ApiError and return JSON response."""
    request_id = get_or_create_request_id()
    response = jsonify(error.to_dict(request_id))
    response.status_code = error.status
    response.headers["X-Request-ID"] = request_id
    return response


def handle_unexpected_exception(error: Exception) -> Response:
    """Handle unexpected exceptions as INTERNAL_ERROR."""
    request_id = get_or_create_request_id()
    
    # Log the full exception for debugging
    logger.exception("Unexpected exception: %s", str(error), extra={"request_id": request_id})
    
    # Return generic error to client (no stack trace, no details)
    api_error = ApiError(
        code="INTERNAL_ERROR",
        status=500,
        message="An internal error occurred. Please contact the administrator.",
    )
    response = jsonify(api_error.to_dict(request_id))
    response.status_code = 500
    response.headers["X-Request-ID"] = request_id
    return response


def setup_error_handlers(app):
    """Register error handlers with the Flask app."""

    @app.before_request
    def before_request():
        """Assign request_id before processing."""
        get_or_create_request_id()

    @app.after_request
    def after_request(response: Response) -> Response:
        """Add X-Request-ID header to every response."""
        request_id = get_or_create_request_id()
        response.headers["X-Request-ID"] = request_id
        return response

    @app.errorhandler(ApiError)
    def handle_api_error_handler(error: ApiError) -> Response:
        """Handle ApiError exceptions."""
        return handle_api_error(error)

    @app.errorhandler(400)
    def handle_400(error):
        """Handle 400 Bad Request (validation)."""
        request_id = get_or_create_request_id()
        api_error = ApiError(
            code="VALIDATION_ERROR",
            status=400,
            message=str(error.description) if hasattr(error, "description") else "Invalid request",
        )
        return handle_api_error(api_error)

    @app.errorhandler(404)
    def handle_404(error):
        """Handle 404 Not Found."""
        request_id = get_or_create_request_id()
        api_error = ApiError(
            code="NOT_FOUND",
            status=404,
            message="Resource not found",
        )
        return handle_api_error(api_error)

    @app.errorhandler(413)
    def handle_413(error):
        """Handle 413 Payload Too Large."""
        request_id = get_or_create_request_id()
        api_error = ApiError(
            code="PAYLOAD_TOO_LARGE",
            status=413,
            message="Request body exceeds maximum allowed size",
        )
        return handle_api_error(api_error)

    @app.errorhandler(Exception)
    def handle_exception(error: Exception) -> Response:
        """Handle unexpected exceptions."""
        # Don't handle HTTPException, let Flask's default handler take it
        if isinstance(error, HTTPException):
            return error
        return handle_unexpected_exception(error)
