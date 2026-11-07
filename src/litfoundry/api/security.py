"""Security headers and origin validation."""

import logging
from typing import Optional
from urllib.parse import urlparse

from flask import request, Response

logger = logging.getLogger(__name__)


# Default CSP header - strict, no inline scripts or unsafe-eval
DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'"
)


def get_configured_origin(app) -> str:
    """Get the configured LitFoundry origin."""
    # Build from request or config
    host = app.config.get("LITFOUNDRY_ALLOWED_HOSTS", "")
    if isinstance(host, str):
        hosts = [h.strip() for h in host.split(",") if h.strip()]
        if hosts:
            host = hosts[0]
        else:
            host = request.host if request else "localhost:5080"
    else:
        host = request.host if request else "localhost:5080"
    
    # Determine scheme
    if request and request.environ.get("HTTP_X_FORWARDED_PROTO"):
        scheme = request.environ.get("HTTP_X_FORWARDED_PROTO")
    else:
        scheme = "https" if request and request.is_secure else "http"
    
    return f"{scheme}://{host}"


def add_security_headers(response: Response, app) -> Response:
    """Add security headers to response."""
    # Content Security Policy
    response.headers["Content-Security-Policy"] = DEFAULT_CSP
    
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Clickjacking protection
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] += "; frame-ancestors 'none'"
    
    return response


def add_cache_headers(response: Response, authenticated: bool = False) -> Response:
    """Add cache control headers based on authentication state."""
    if authenticated:
        # Authenticated responses should not be cached
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    else:
        # For now, public responses also don't cache
        # This can be tuned per endpoint
        response.headers["Cache-Control"] = "no-cache"
    
    return response


def check_origin(app) -> Optional[tuple]:
    """Check Origin/Referer header for unsafe methods. Return error tuple if denied."""
    # Only check unsafe methods
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    
    # Exempt setup endpoints from origin check (they run before frontend exists)
    if request.path.startswith("/api/v1/setup/"):
        return None
    
    # Get request origin
    origin = request.headers.get("Origin")
    if not origin:
        # Fall back to Referer
        referer = request.headers.get("Referer")
        if referer:
            try:
                origin = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
            except Exception:
                origin = None
    
    if not origin:
        # Missing origin on unsafe request - reject
        return (
            {
                "code": "FORBIDDEN",
                "status": 403,
                "message": "Origin header required for state-changing requests",
            },
            403,
        )
    
    # Get configured allowed origins
    configured_origin = get_configured_origin(app)
    cross_origin_allowlist = app.config.get("LITFOUNDRY_CORS_ORIGINS", "")
    if isinstance(cross_origin_allowlist, str):
        cross_origin_allowlist = [o.strip() for o in cross_origin_allowlist.split(",") if o.strip()]
    
    # Check if origin matches configured or allowlisted
    if origin == configured_origin or origin in cross_origin_allowlist:
        return None
    
    # Origin not allowed
    logger.warning(
        "Cross-origin request rejected",
        extra={"origin": origin, "configured": configured_origin},
    )
    return (
        {
            "code": "FORBIDDEN",
            "status": 403,
            "message": "Cross-origin requests are not allowed",
        },
        403,
    )


def safe_redirect(return_path: Optional[str], default: str = "/") -> str:
    """Return a safe redirect path (relative only, no open redirects).
    
    Args:
        return_path: The requested return path
        default: Default path if return_path is invalid
    
    Returns:
        A safe relative path
    """
    if not return_path:
        return default
    
    # Must be relative (start with /)
    if not return_path.startswith("/"):
        return default
    
    # Must not be a full URL (no scheme or netloc)
    parsed = urlparse(return_path)
    if parsed.scheme or parsed.netloc:
        return default
    
    # Looks safe
    return return_path


def ignore_query_string_tokens(request_obj=None):
    """Log if tokens appear in query strings (should be ignored).
    
    This checks for common token parameter names and logs a warning if found.
    The actual token verification should ignore query string tokens.
    """
    if not request_obj:
        request_obj = request
    
    # Common token parameter names
    token_params = ["token", "access_token", "refresh_token", "api_key", "key"]
    
    for param in token_params:
        if param in request_obj.args:
            logger.warning(
                "Token found in query string - ignoring",
                extra={"param": param},
            )


def setup_security_middleware(app):
    """Register security middleware with Flask app."""

    @app.after_request
    def after_request_security(response: Response) -> Response:
        """Add security headers after each request."""
        add_security_headers(response, app)
        
        # Add cache headers (check if request was authenticated)
        authenticated = hasattr(request, "user") and request.user is not None
        add_cache_headers(response, authenticated=authenticated)
        
        # Log any query string tokens
        ignore_query_string_tokens()
        
        return response

    @app.before_request
    def before_request_origin_check():
        """Check origin for unsafe requests."""
        error_result = check_origin(app)
        if error_result:
            from flask import jsonify
            error_dict, status = error_result
            from litfoundry.api.errors import get_or_create_request_id
            request_id = get_or_create_request_id()
            error_dict["request_id"] = request_id
            response = jsonify(error_dict)
            response.status_code = status
            response.headers["X-Request-ID"] = request_id
            return response
