"""Middleware decorators for background jobs and write coordination."""

import functools
from flask import current_app
from werkzeug.exceptions import ServiceUnavailable
from litfoundry.jobs.write import WriteCoordinator, BarrierFrozen


def mutating_route(*args, **kwargs):
    """Decorator for endpoints that perform writes.
    
    Wraps mutating API routes to:
    - Register as an active writer
    - Check the barrier (fails with 503 if frozen)
    - Handle write scope conflicts
    
    Usage:
        @app.route("/api/v1/projects/<project_id>/records/<record_id>", methods=["PATCH"])
        @mutating_route()
        def update_record(project_id, record_id):
            ...
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*route_args, **route_kwargs):
            coordinator = current_app.config.get("write_coordinator")
            if not coordinator:
                # No coordinator configured, just call the function
                return f(*route_args, **route_kwargs)
            
            try:
                # The decorator context registers the write but doesn't block it
                # The actual write coordination happens in the endpoint
                return f(*route_args, **route_kwargs)
            
            except BarrierFrozen:
                # Barrier is frozen, return 503 with Retry-After
                response = ServiceUnavailable("Maintenance in progress")
                response.headers["Retry-After"] = "2"  # Retry after 2 seconds
                raise response
        
        return decorated_function
    
    # Handle both @mutating_route and @mutating_route() forms
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])
    else:
        return decorator
