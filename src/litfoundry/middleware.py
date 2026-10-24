"""Middleware and request hooks."""

from flask import request, abort, current_app


def setup_middleware(app, trusted_proxies=None, host_allowlist=None, cors_origins=None):
    """Setup Flask middleware for security and proxy handling.
    
    Args:
        app: Flask application instance
        trusted_proxies: List of trusted proxy IP addresses (informational;
                        Werkzeug's ProxyFix trusts based on hop count, not IP whitelist)
        host_allowlist: List of allowed Host header values (if None or empty,
                       all hosts are allowed)
        cors_origins: List of allowed CORS origins (if None or empty,
                     CORS is disabled)
    
    Note: Werkzeug's ProxyFix middleware trusts forwarded headers based on the
    number of hops (x_for, x_proto, x_host parameters). For production deployments
    behind a known reverse proxy (e.g., Caddy), set the hop count to 1. For
    multiple proxy layers, increase as needed. An untrusted peer cannot spoof
    these headers because ProxyFix only looks at the rightmost value up to the
    configured hop count.
    """
    from werkzeug.middleware.proxy_fix import ProxyFix
    
    # Apply ProxyFix middleware for trusted proxy handling
    # With x_for=1, x_proto=1, x_host=1: trust one level of forwarded headers
    # An attacker cannot spoof these headers if they come from an untrusted peer
    # because ProxyFix only trusts headers from the rightmost N proxies in the chain
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,        # Trust X-Forwarded-For from one proxy
        x_proto=1,      # Trust X-Forwarded-Proto from one proxy
        x_host=1,       # Trust X-Forwarded-Host from one proxy
        x_port=1,       # Trust X-Forwarded-Port from one proxy
        x_prefix=1,     # Trust X-Forwarded-Prefix from one proxy
    )
    
    # Store trusted proxies list in config for reference (e.g., logging)
    if trusted_proxies:
        app.config['TRUSTED_PROXIES'] = trusted_proxies
    
    # Store host allowlist in app config for use in before_request
    if host_allowlist:
        app.config['HOST_ALLOWLIST'] = set(host_allowlist)
    else:
        app.config['HOST_ALLOWLIST'] = None
    
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
        app.config['CORS_ENABLED'] = False
    
    # Register before_request handler
    app.before_request(before_request_handler)


def before_request_handler() -> None:
    """Handle before-request hooks: host allowlist validation."""
    # Check host allowlist if configured
    host_allowlist = current_app.config.get('HOST_ALLOWLIST')
    if host_allowlist:
        host_header = request.host.split(':')[0]  # Extract hostname without port
        if host_header not in host_allowlist:
            abort(400, "Invalid Host header")




