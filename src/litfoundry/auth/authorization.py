"""Project access control and authorization.

Implements the access resolution order:
1. Admin (system)
2. Owner
3. Explicit ACL (editor, viewer, or deny)
4. Public default (editor or viewer)
5. Deny (no access)

All disabled accounts are denied access regardless of other rules.
"""

from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Optional, Callable
from uuid import UUID

from flask import request, current_app, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import select
from sqlalchemy.orm import Session, scoped_session

from litfoundry.catalog.models import User, ProjectDirectory, ProjectACL
from litfoundry.api.errors import ApiError


class AccessLevel(str, Enum):
    """Access levels for projects."""
    NONE = "none"
    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"
    ADMIN = "admin"


class AccessRule(str, Enum):
    """Rules that determine access."""
    ADMIN = "admin"
    OWNER = "owner"
    EXPLICIT_GRANT = "explicit_grant"
    EXPLICIT_DENY = "explicit_deny"
    PUBLIC_ACCESS = "public_access"
    DEFAULT_DENY = "default_deny"


@dataclass
class AuthorizationDecision:
    """Result of an authorization check."""
    level: AccessLevel
    rule: AccessRule
    
    def allows_action(self, required_level: AccessLevel) -> bool:
        """Check if this access level allows the required action."""
        level_order = [
            AccessLevel.NONE,
            AccessLevel.VIEWER,
            AccessLevel.EDITOR,
            AccessLevel.OWNER,
            AccessLevel.ADMIN,
        ]
        
        if self.level == AccessLevel.NONE:
            return False
        
        level_idx = level_order.index(self.level)
        required_idx = level_order.index(required_level)
        return level_idx >= required_idx


def authorize(
    user: User,
    project_id: str,
    session: Session,
) -> AuthorizationDecision:
    """
    Resolve access to a project for a user.
    
    Resolution order:
    1. Disabled accounts are always denied
    2. Admin gets full access
    3. Owner gets full access
    4. Explicit ACL entry (editor, viewer, or deny)
    5. Public default (editor or viewer)
    6. Otherwise, deny
    
    Args:
        user: The user requesting access
        project_id: UUID of the project
        session: SQLAlchemy session for database access
    
    Returns:
        AuthorizationDecision with access level and the rule that determined it
    """
    
    # Rule 1: Disabled accounts are always denied
    if not user.active:
        return AuthorizationDecision(
            level=AccessLevel.NONE,
            rule=AccessRule.DEFAULT_DENY,
        )
    
    # Get project directory entry
    project = session.scalar(
        select(ProjectDirectory).where(ProjectDirectory.id == project_id)
    )
    if not project:
        # Project not found = no access
        return AuthorizationDecision(
            level=AccessLevel.NONE,
            rule=AccessRule.DEFAULT_DENY,
        )
    
    # Rule 2: Admin (system) gets full access
    if user.role == "admin":
        return AuthorizationDecision(
            level=AccessLevel.ADMIN,
            rule=AccessRule.ADMIN,
        )
    
    # Rule 3: Owner gets full access
    if project.owner_user_id == user.id:
        return AuthorizationDecision(
            level=AccessLevel.OWNER,
            rule=AccessRule.OWNER,
        )
    
    # Rule 4: Check explicit ACL entry
    acl_entry = session.scalar(
        select(ProjectACL).where(
            ProjectACL.project_id == project_id,
            ProjectACL.user_id == user.id,
        )
    )
    
    if acl_entry:
        if acl_entry.role == "deny":
            return AuthorizationDecision(
                level=AccessLevel.NONE,
                rule=AccessRule.EXPLICIT_DENY,
            )
        elif acl_entry.role == "editor":
            return AuthorizationDecision(
                level=AccessLevel.EDITOR,
                rule=AccessRule.EXPLICIT_GRANT,
            )
        elif acl_entry.role == "viewer":
            return AuthorizationDecision(
                level=AccessLevel.VIEWER,
                rule=AccessRule.EXPLICIT_GRANT,
            )
    
    # Rule 5: Public default
    if project.public_access == "editor":
        return AuthorizationDecision(
            level=AccessLevel.EDITOR,
            rule=AccessRule.PUBLIC_ACCESS,
        )
    elif project.public_access == "viewer":
        return AuthorizationDecision(
            level=AccessLevel.VIEWER,
            rule=AccessRule.PUBLIC_ACCESS,
        )
    
    # Rule 6: Default deny
    return AuthorizationDecision(
        level=AccessLevel.NONE,
        rule=AccessRule.DEFAULT_DENY,
    )


def project_permission(required_level: AccessLevel | str) -> Callable:
    """
    Decorator for project endpoints requiring permission checks.
    
    Expects the route to have a project_id parameter (as a URL parameter).
    
    Returns:
        - 404 NOT_FOUND if the project is undiscoverable (user cannot see it)
        - 403 FORBIDDEN if the user can see the project but doesn't have sufficient rights
        - Calls the wrapped function if authorized
    
    Args:
        required_level: The minimum access level required (viewer, editor, owner, or admin)
    """
    if isinstance(required_level, str):
        required_level = AccessLevel(required_level)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Verify JWT authentication
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
            except Exception:
                raise ApiError(
                    code="UNAUTHORIZED",
                    status=401,
                    message="Authentication required"
                )
            
            # Get the project_id from the request (either from URL or kwargs)
            project_id = request.view_args.get("project_id") or kwargs.get("project_id")
            if not project_id:
                raise ApiError(
                    code="BAD_REQUEST",
                    status=400,
                    message="project_id not found in request"
                )
            
            # Get database session
            db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
            try:
                # Get user
                user = db_session.query(User).filter_by(id=user_id).first()
                if not user:
                    raise ApiError(
                        code="UNAUTHORIZED",
                        status=401,
                        message="User not found"
                    )
                
                # Authorize
                decision = authorize(user, project_id, db_session)
                
                # Check if user can discover the project (can read it)
                if decision.level == AccessLevel.NONE:
                    # Check if project exists at all
                    project_exists = db_session.query(ProjectDirectory).filter_by(
                        id=project_id
                    ).first() is not None
                    
                    if project_exists:
                        # Project exists but user can't see it, return 403
                        raise ApiError(
                            code="FORBIDDEN",
                            status=403,
                            message="Insufficient permissions for this project"
                        )
                    else:
                        # Project doesn't exist, return 404 to not reveal existence
                        raise ApiError(
                            code="NOT_FOUND",
                            status=404,
                            message="Project not found"
                        )
                
                # Check if user has sufficient level
                if not decision.allows_action(required_level):
                    raise ApiError(
                        code="FORBIDDEN",
                        status=403,
                        message=f"Requires {required_level.value} access or higher"
                    )
                
                # Store the user and decision in request context for the handler
                request.project_user = user
                request.project_decision = decision
                
                # Call the wrapped function
                return func(*args, **kwargs)
            finally:
                db_session.remove()
        
        return wrapper
    return decorator
