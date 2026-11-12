"""Middleware and request hooks."""

from flask import abort, current_app, request


def setup_middleware(app, trusted_proxies=None, host_allowlist=None, cors_origins=None):
    """Set up Flask middleware for security and proxy handling.

    Args:
        app: Flask application instance
        trusted_proxies: List of trusted proxy IP addresses. ProxyFix will only
                        trust X-Forwarded-* headers from these IPs (or via IPv6
                        prefix validation). If None/empty, ProxyFix trusts based
                        on hop count (1 hop by default), which is unsafe for
                        untrusted networks.
        host_allowlist: List of allowed Host header values (if None or empty,
                       all hosts are allowed)
        cors_origins: List of allowed CORS origins (if None or empty,
                     CORS is disabled)

    Note:
        For production deployments, ALWAYS configure trusted_proxies with
        the IP addresses of your reverse proxy(ies). This ensures ProxyFix only
        trusts forwarded headers from known sources, preventing header spoofing
        from untrusted peers.

    """
    from werkzeug.middleware.proxy_fix import ProxyFix

    # Store trusted proxies for IP validation
    # Must be stored BEFORE wrapping with middleware
    if trusted_proxies:
        app.config["TRUSTED_PROXIES"] = set(trusted_proxies)
    else:
        app.config["TRUSTED_PROXIES"] = None

    # Store host allowlist in app config for use in before_request
    if host_allowlist:
        app.config["HOST_ALLOWLIST"] = set(host_allowlist)
    else:
        app.config["HOST_ALLOWLIST"] = None

    # Apply middleware in this order (innermost to outermost in WSGI chain):
    # 1. _CaptureRemoteAddrMiddleware - captures original REMOTE_ADDR FIRST
    # 2. ProxyFix - modifies REMOTE_ADDR based on X-Forwarded-* headers
    # So execution order (request comes in → execution):
    # ProxyFix → _CaptureRemoteAddrMiddleware → Flask app
    # But _CaptureRemoteAddrMiddleware runs first to capture original REMOTE_ADDR

    if trusted_proxies:
        # First wrap with ProxyFix (will be outermost in WSGI chain)
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,  # Trust X-Forwarded-For from one proxy
            x_proto=1,  # Trust X-Forwarded-Proto from one proxy
            x_host=1,  # Trust X-Forwarded-Host from one proxy
            x_port=1,  # Trust X-Forwarded-Port from one proxy
            x_prefix=1,  # Trust X-Forwarded-Prefix from one proxy
        )

        # Then wrap with _CaptureRemoteAddrMiddleware (will be innermost in WSGI chain)
        # This runs BEFORE ProxyFix and captures the original REMOTE_ADDR
        app.wsgi_app = _CaptureRemoteAddrMiddleware(app.wsgi_app, app.config)

    # Setup CORS with same-origin default (no wildcard, credentials allowed)
    if cors_origins:
        from flask_cors import CORS

        CORS(
            app,
            origins=cors_origins,
            supports_credentials=True,
            allow_headers=["Content-Type", "Authorization"],
            methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        )
    else:
        # No CORS config means cross-origin requests are refused
        app.config["CORS_ENABLED"] = False

    # Register before_request handler
    app.before_request(before_request_handler)


class _CaptureRemoteAddrMiddleware:
    """WSGI middleware that captures the original REMOTE_ADDR before ProxyFix runs.

    This middleware saves the actual peer IP address to a custom environ variable
    before ProxyFix has a chance to modify REMOTE_ADDR based on X-Forwarded-* headers.
    We then validate this original peer address against the trusted proxy list.
    """

    def __init__(self, app, app_config):
        """Initialize the middleware.

        Args:
            app: The WSGI application to wrap
            app_config: Flask app.config dict (to access TRUSTED_PROXIES)

        """
        self.app = app
        self.app_config = app_config

    def __call__(self, environ, start_response):
        """Capture original REMOTE_ADDR and validate against trusted proxies.

        Args:
            environ: WSGI environment dict
            start_response: WSGI start_response callable

        Raises:
            403 Forbidden if REMOTE_ADDR is not in trusted proxies list

        """
        # Save original REMOTE_ADDR before ProxyFix modifies it
        # Use a custom environ key to preserve the original peer IP
        original_remote_addr = environ.get("REMOTE_ADDR", "unknown")
        environ["litfoundry.original_remote_addr"] = original_remote_addr

        # Validate original peer against trusted proxies
        trusted_proxies = self.app_config.get("TRUSTED_PROXIES")
        if trusted_proxies is not None:
            if original_remote_addr not in trusted_proxies:
                # Untrusted peer - reject immediately
                # Return a 403 Forbidden response
                status = "403 Forbidden"
                headers = [("Content-Type", "text/html; charset=utf-8")]
                start_response(status, headers)
                error_msg = (
                    f"Untrusted proxy IP: {original_remote_addr} " f"(not in trusted proxies list)"
                )
                html = f"<html><body><h1>403 Forbidden</h1>" f"<p>{error_msg}</p></body></html>"
                return [html.encode("utf-8")]

        # Peer is trusted (or no proxy trust configured) - proceed
        return self.app(environ, start_response)


def before_request_handler() -> None:
    """Handle before-request hooks: trusted proxy validation and host allowlist.

    Validates:
    1. If trusted_proxies configured, connection was from a trusted IP
       (validated in _CaptureRemoteAddrMiddleware WSGI layer)
    2. If host_allowlist configured, verify Host header is in allowlist
    """
    # Proxy validation is done at WSGI layer (_CaptureRemoteAddrMiddleware),
    # so if we reach here, the connection is either from a trusted proxy or
    # no proxy trust is configured.

    # Check host allowlist if configured
    host_allowlist = current_app.config.get("HOST_ALLOWLIST")
    if host_allowlist:
        host_header = request.host.split(":")[0]  # Extract hostname without port
        if host_header not in host_allowlist:
            abort(400, "Invalid Host header")
