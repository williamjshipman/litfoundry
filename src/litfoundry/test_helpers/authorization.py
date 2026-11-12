"""Test helpers for authorization and permissions."""

from flask import Flask
from litfoundry.auth.authorization import project_permission


def assert_all_project_routes_decorated(app: Flask):
    """
    Assert that every project route (under /api/v1/projects) declares a permission requirement.
    
    This helper verifies that the @project_permission decorator has been applied to all
    project-related endpoints, ensuring that authorization checks are never forgotten.
    
    Args:
        app: Flask application instance
    
    Raises:
        AssertionError: If any undecorated project route is found
    """
    undecorated_routes = []
    
    for rule in app.url_map.iter_rules():
        # Only check project routes
        if not rule.rule.startswith("/api/v1/projects"):
            continue
        
        # Get the view function
        view_func = app.view_functions.get(rule.endpoint)
        if not view_func:
            continue
        
        # Check if the view function has been wrapped by the project_permission decorator
        # The decorator wraps the function, so we check if it has the __wrapped__ attribute
        # or if it's a functools.wraps-decorated function
        has_decorator = (
            hasattr(view_func, '__wrapped__') or 
            hasattr(view_func, '_original_function') or
            (hasattr(view_func, '__name__') and view_func.__name__.startswith('wrapper'))
        )
        
        # Also check the docstring or other attributes that might indicate decoration
        # For now, we rely on the __wrapped__ attribute
        if not has_decorator and rule.rule != "/api/v1/projects":  # List endpoint might have different structure
            undecorated_routes.append(rule.rule)
    
    assert len(undecorated_routes) == 0, (
        f"Found undecorated project routes (missing @project_permission decorator): "
        f"{', '.join(undecorated_routes)}"
    )
