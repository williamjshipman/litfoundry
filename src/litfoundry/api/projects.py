"""Project API endpoints."""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from sqlalchemy import select, or_
from sqlalchemy.orm import scoped_session
from uuid import uuid4
from collections import defaultdict
from time import time

from litfoundry.catalog.models import User, ProjectDirectory, ProjectACL, AuditEvent
from litfoundry.auth.authorization import authorize, AccessLevel, project_permission
from litfoundry.api.errors import ApiError
from litfoundry.api.pagination import parse_pagination_params

bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")

# Rate limiting: token bucket per user (30 requests per minute)
_rate_limit_buckets = {}  # {user_id: {"tokens": float, "last_update": float}}
_RATE_LIMIT_TOKENS = 30
_RATE_LIMIT_WINDOW_SECONDS = 60


def _check_rate_limit(user_id: str) -> bool:
    """Check if user has exceeded rate limit for user lookup."""
    now = time()
    
    if user_id not in _rate_limit_buckets:
        _rate_limit_buckets[user_id] = {"tokens": _RATE_LIMIT_TOKENS, "last_update": now}
        return True
    
    bucket = _rate_limit_buckets[user_id]
    elapsed = now - bucket["last_update"]
    
    # Refill tokens based on elapsed time
    bucket["tokens"] = min(
        _RATE_LIMIT_TOKENS,
        bucket["tokens"] + (elapsed * _RATE_LIMIT_TOKENS / _RATE_LIMIT_WINDOW_SECONDS)
    )
    bucket["last_update"] = now
    
    if bucket["tokens"] >= 1:
        bucket["tokens"] -= 1
        return True
    
    return False


def log_admin_project_access(user_id: str, project_id: str):
    """Log admin access to a project to audit_events."""
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Only log for admin users
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user or user.role != "admin":
            return
        
        # Get project
        project = db_session.query(ProjectDirectory).filter_by(id=project_id).first()
        if not project:
            return
        
        # Only log if admin doesn't own the project
        if project.owner_user_id == user_id:
            return
        
        # Log the access
        event = AuditEvent(
            id=str(uuid4()),
            actor_user_id=user_id,
            action="project_opened",
            resource_type="project",
            resource_id=project_id,
            details=f"Admin opened project '{project.title}'",
            status="success",
            error_message=None,
            request_id=request.headers.get("X-Request-ID", str(uuid4())),
            ip_address=request.remote_addr or "unknown",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(event)
        db_session.commit()
    except Exception as e:
        current_app.logger.warning(f"Failed to log admin project access: {str(e)}")
    finally:
        db_session.remove()


@bp.route("", methods=["GET"])

def list_projects():
    """List projects accessible to the current user.
    
    Returns projects that the user can discover (read access or higher).
    Projects are filtered through the authorization service.
    
    Returns:
        {
            "items": [
                {
                    "id": "uuid",
                    "title": "Project Title",
                    "owner_user_id": "uuid",
                    "public_access": "none|viewer|editor",
                    "state_code": "ready|archived",
                    "created_at": "ISO8601",
                    "updated_at": "ISO8601"
                }
            ],
            "pagination": {
                "offset": 0,
                "limit": 20,
                "total": 100
            }
        }
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception:
        raise ApiError(
            code="UNAUTHORIZED",
            status=401,
            message="Authentication required"
        )
    
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
        
        # Get pagination parameters
        pagination = parse_pagination_params(request.args)
        offset = 0  # For now, not using cursor-based pagination
        limit = pagination.limit
        
        # Query all projects in catalogue
        all_projects = db_session.query(ProjectDirectory).all()
        
        # Filter through authorization service
        accessible_projects = []
        for project in all_projects:
            decision = authorize(user, project.id, db_session)
            # User must be able to read (discover) the project
            if decision.level in [AccessLevel.VIEWER, AccessLevel.EDITOR, AccessLevel.OWNER, AccessLevel.ADMIN]:
                accessible_projects.append(project)
        
        # Apply pagination
        total_count = len(accessible_projects)
        paginated_projects = accessible_projects[offset:offset + limit]
        
        # Build response
        items = []
        for project in paginated_projects:
            items.append({
                "id": project.id,
                "title": project.title,
                "owner_user_id": project.owner_user_id,
                "public_access": project.public_access,
                "state_code": project.state_code,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            })
        
        return jsonify({
            "items": items,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
            }
        })
    finally:
        db_session.remove()


@bp.route("/<project_id>", methods=["GET"])
@project_permission(AccessLevel.VIEWER)
def get_project(project_id: str):
    """Get a specific project.
    
    Returns project metadata and logs admin access if applicable.
    
    Returns:
        {
            "id": "uuid",
            "title": "Project Title",
            "owner_user_id": "uuid",
            "public_access": "none|viewer|editor",
            "state_code": "ready|archived",
            "created_at": "ISO8601",
            "updated_at": "ISO8601"
        }
    """
    # Log admin access
    log_admin_project_access(get_jwt_identity(), project_id)
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        project = db_session.query(ProjectDirectory).filter_by(id=project_id).first()
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        return jsonify({
            "id": project.id,
            "title": project.title,
            "owner_user_id": project.owner_user_id,
            "public_access": project.public_access,
            "state_code": project.state_code,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        })
    finally:
        db_session.remove()


@bp.route("/<project_id>/sharing", methods=["GET"])
@project_permission(AccessLevel.VIEWER)
def get_sharing(project_id: str):
    """Get sharing settings and effective permissions for a project.
    
    Returns visibility, ACL entries, and effective permissions for each listed user.
    
    Returns:
        {
            "project_id": "uuid",
            "visibility": "none|viewer|editor",
            "acl": [
                {
                    "user_id": "uuid",
                    "role": "viewer|editor|deny",
                    "granted_at": "ISO8601"
                }
            ],
            "effective_permissions": [
                {
                    "user_id": "uuid",
                    "username": "user",
                    "access_level": "viewer|editor|owner|admin",
                    "rule": "owner|admin|explicit_grant|explicit_deny|public_access|default_deny"
                }
            ]
        }
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Verify project exists
        project = db_session.query(ProjectDirectory).filter_by(id=project_id).first()
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        # Get ACL entries
        acl_entries = db_session.query(ProjectACL).filter_by(project_id=project_id).all()
        
        # Build ACL list
        acl_list = []
        for entry in acl_entries:
            acl_list.append({
                "user_id": entry.user_id,
                "role": entry.role,
                "granted_at": entry.granted_at.isoformat(),
            })
        
        # Build effective permissions list
        # Include: owner, all ACL users, and public access users (if public)
        effective_perms = []
        
        # Owner
        owner = db_session.query(User).filter_by(id=project.owner_user_id).first()
        if owner:
            effective_perms.append({
                "user_id": owner.id,
                "username": owner.username,
                "access_level": "owner",
                "rule": "owner",
            })
        
        # ACL users
        for entry in acl_entries:
            user = db_session.query(User).filter_by(id=entry.user_id).first()
            if user:
                decision = authorize(user, project_id, db_session)
                effective_perms.append({
                    "user_id": user.id,
                    "username": user.username,
                    "access_level": decision.level.value,
                    "rule": decision.rule.value,
                })
        
        return jsonify({
            "project_id": project_id,
            "visibility": project.public_access,
            "acl": acl_list,
            "effective_permissions": effective_perms,
        })
    finally:
        db_session.remove()


@bp.route("/<project_id>/sharing", methods=["PUT"])
@project_permission(AccessLevel.OWNER)
def update_sharing(project_id: str):
    """Update sharing settings for a project.
    
    Only owners and admins can update sharing.
    
    Request body:
        {
            "visibility": "none|viewer|editor",  # Optional
            "public_edit_confirmation": true,     # Required if setting visibility to "editor"
            "acl": [
                {"user_id": "uuid", "role": "viewer|editor|deny"},
                ...
            ]
        }
    
    Returns the updated sharing settings.
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Verify project exists
        project = db_session.query(ProjectDirectory).filter_by(id=project_id).first()
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        # Check authorization (must be owner or admin)
        user_id = get_jwt_identity()
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ApiError(
                code="UNAUTHORIZED",
                status=401,
                message="User not found"
            )
        
        decision = authorize(user, project_id, db_session)
        if decision.level not in [AccessLevel.OWNER, AccessLevel.ADMIN]:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Only owner and admin can update sharing"
            )
        
        data = request.get_json() or {}
        
        # Update visibility if provided
        if "visibility" in data:
            visibility = data["visibility"]
            if visibility not in ["none", "viewer", "editor"]:
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="Invalid visibility value"
                )
            
            # Check for public edit confirmation
            if visibility == "editor" and not data.get("public_edit_confirmation"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="Public edit confirmation required"
                )
            
            project.public_access = visibility
        
        # Update ACL if provided
        if "acl" in data:
            acl_data = data["acl"]
            
            # Clear existing ACL entries
            db_session.query(ProjectACL).filter_by(project_id=project_id).delete()
            
            # Add new ACL entries
            for entry in acl_data:
                user_id_acl = entry.get("user_id")
                role = entry.get("role")
                
                if not user_id_acl or not role:
                    raise ApiError(
                        code="VALIDATION_ERROR",
                        status=400,
                        message="Invalid ACL entry"
                    )
                
                if role not in ["viewer", "editor", "deny"]:
                    raise ApiError(
                        code="VALIDATION_ERROR",
                        status=400,
                        message="Invalid role"
                    )
                
                # Don't allow deny for admin
                if role == "deny" and user_id_acl == "admin":
                    raise ApiError(
                        code="VALIDATION_ERROR",
                        status=400,
                        message="Cannot deny admin access"
                    )
                
                acl_entry = ProjectACL(
                    id=str(uuid4()),
                    project_id=project_id,
                    user_id=user_id_acl,
                    role=role,
                    granted_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db_session.add(acl_entry)
        
        project.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Return updated sharing settings
        return get_sharing(project_id)
    finally:
        db_session.remove()


@bp.route("/<project_id>/audit-events", methods=["GET"])
@project_permission(AccessLevel.VIEWER)
def get_audit_events(project_id: str):
    """Get audit events for a project.
    
    Merges catalogue audit events (sharing, admin access) with project audit events.
    Paginated and filterable by actor, action, and time.
    
    Query parameters:
        - actor_user_id: Filter by actor (optional)
        - action: Filter by action (optional)
        - limit: Maximum results (default 50, max 500)
        - offset: Results offset (default 0)
    
    Returns:
        {
            "items": [
                {
                    "id": "uuid",
                    "actor_user_id": "uuid",
                    "action": "project_opened",
                    "resource_type": "project",
                    "resource_id": "uuid",
                    "details": "Admin opened project",
                    "created_at": "ISO8601"
                }
            ],
            "pagination": {
                "offset": 0,
                "limit": 50,
                "total": 100
            }
        }
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Verify project exists
        project = db_session.query(ProjectDirectory).filter_by(id=project_id).first()
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        # Get audit events from catalogue (admin access, sharing changes)
        actor_user_id = request.args.get("actor_user_id")
        action = request.args.get("action")
        limit = min(int(request.args.get("limit", "50")), 500)
        offset = int(request.args.get("offset", "0"))
        
        # Query catalogue audit events for this project
        query = db_session.query(AuditEvent).filter(
            AuditEvent.resource_type == "project",
            AuditEvent.resource_id == project_id,
        )
        
        if actor_user_id:
            query = query.filter(AuditEvent.actor_user_id == actor_user_id)
        
        if action:
            query = query.filter(AuditEvent.action == action)
        
        # Sort by created_at descending
        query = query.order_by(AuditEvent.created_at.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        events = query.offset(offset).limit(limit).all()
        
        # Build response
        items = []
        for event in events:
            items.append({
                "id": event.id,
                "actor_user_id": event.actor_user_id,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "details": event.details,
                "created_at": event.created_at.isoformat(),
            })
        
        return jsonify({
            "items": items,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
            }
        })
    finally:
        db_session.remove()


# User lookup endpoint (separate blueprint section for clarity)
users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@users_bp.route("/lookup", methods=["GET"])
def lookup_users():
    """Search for enabled users by username or display name.
    
    Rate-limited to 30 requests per minute per user.
    Returns only UUID, username, and display name (no email or sensitive data).
    
    Query parameters:
        - q: Search term (username or display name substring)
        - limit: Maximum results (default 20, max 100)
    
    Returns:
        {
            "items": [
                {
                    "id": "uuid",
                    "username": "user",
                    "display_name": "User Name"
                }
            ]
        }
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception:
        raise ApiError(
            code="UNAUTHORIZED",
            status=401,
            message="Authentication required"
        )
    
    # Check rate limit
    if not _check_rate_limit(user_id):
        raise ApiError(
            code="RATE_LIMITED",
            status=429,
            message="Too many requests. Maximum 30 per minute."
        )
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        query_term = request.args.get("q", "").strip()
        limit = min(int(request.args.get("limit", "20")), 100)
        
        if not query_term:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Search term 'q' is required"
            )
        
        if len(query_term) < 2:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Search term must be at least 2 characters"
            )
        
        # Search for enabled users
        # Match username or display name (case-insensitive)
        term_lower = query_term.lower()
        results = db_session.query(User).filter(
            User.active == True,
            or_(
                User.username_normalized.ilike(f"%{term_lower}%"),
                User.username.ilike(f"%{query_term}%"),
            )
        ).limit(limit).all()
        
        # Build response (no email field)
        items = []
        for user in results:
            items.append({
                "id": user.id,
                "username": user.username,
                "display_name": user.username,  # Use username as display name for now
            })
        
        return jsonify({
            "items": items,
        })
    finally:
        db_session.remove()


# Admin endpoints for project quarantine/release
admin_bp = Blueprint("admin_projects", __name__, url_prefix="/api/v1/admin/projects")


@admin_bp.route("/<project_id>/quarantine", methods=["POST"])
def quarantine_project(project_id: str):
    """Admin: Quarantine a project (admin only)."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception:
        raise ApiError(
            code="UNAUTHORIZED",
            status=401,
            message="Authentication required"
        )
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Check admin status
        user = db_session.query(User).filter(User.id == user_id).one_or_none()
        if not user or not user.is_admin:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Admin access required"
            )
        
        # Check project exists
        project = db_session.query(ProjectDirectory).filter(
            ProjectDirectory.id == project_id
        ).one_or_none()
        
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        # Quarantine
        project.state = "quarantined"
        project.updated_at = datetime.now(timezone.utc)
        
        # Record audit event
        audit = AuditEvent(
            actor_user_id=user_id,
            action="quarantine",
            resource_type="project",
            resource_id=project_id,
        )
        db_session.add(audit)
        db_session.commit()
        
        return jsonify({"status": "quarantined"})
    finally:
        db_session.remove()


@admin_bp.route("/<project_id>/release", methods=["POST"])
def release_project(project_id: str):
    """Admin: Release a quarantined project (admin only)."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception:
        raise ApiError(
            code="UNAUTHORIZED",
            status=401,
            message="Authentication required"
        )
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Check admin status
        user = db_session.query(User).filter(User.id == user_id).one_or_none()
        if not user or not user.is_admin:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Admin access required"
            )
        
        # Check project exists
        project = db_session.query(ProjectDirectory).filter(
            ProjectDirectory.id == project_id
        ).one_or_none()
        
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        # Release
        project.state = "ready"
        project.updated_at = datetime.now(timezone.utc)
        
        # Record audit event
        audit = AuditEvent(
            actor_user_id=user_id,
            action="release",
            resource_type="project",
            resource_id=project_id,
        )
        db_session.add(audit)
        db_session.commit()
        
        return jsonify({"status": "ready"})
    finally:
        db_session.remove()


@admin_bp.route("/<project_id>/transfer-to", methods=["POST"])
def admin_transfer_project(project_id: str):
    """Admin: Transfer project to another owner (admin only)."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception:
        raise ApiError(
            code="UNAUTHORIZED",
            status=401,
            message="Authentication required"
        )
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Check admin status
        user = db_session.query(User).filter(User.id == user_id).one_or_none()
        if not user or not user.is_admin:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Admin access required"
            )
        
        data = request.get_json() or {}
        new_owner_id = data.get("owner_id", "").strip()
        
        if not new_owner_id:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="owner_id is required"
            )
        
        # Check project exists
        project = db_session.query(ProjectDirectory).filter(
            ProjectDirectory.id == project_id
        ).one_or_none()
        
        if not project:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="Project not found"
            )
        
        # Check new owner exists
        new_owner = db_session.query(User).filter(User.id == new_owner_id).one_or_none()
        if not new_owner:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="New owner does not exist"
            )
        
        # Transfer
        project.owner_id = new_owner_id
        project.updated_at = datetime.now(timezone.utc)
        
        # Record audit event
        audit = AuditEvent(
            actor_user_id=user_id,
            action="transfer_ownership",
            resource_type="project",
            resource_id=project_id,
            details=f"to {new_owner_id}",
        )
        db_session.add(audit)
        db_session.commit()
        
        return jsonify({"status": "transferred"})
    finally:
        db_session.remove()


# Endpoint to transfer all projects from one user to another
@admin_bp.route("/transfer-all", methods=["POST"])
def transfer_all_user_projects():
    """Admin: Transfer all projects from one user to another (admin only)."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception:
        raise ApiError(
            code="UNAUTHORIZED",
            status=401,
            message="Authentication required"
        )
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Check admin status
        user = db_session.query(User).filter(User.id == user_id).one_or_none()
        if not user or not user.is_admin:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Admin access required"
            )
        
        data = request.get_json() or {}
        from_user_id = data.get("from_user_id", "").strip()
        to_user_id = data.get("to_user_id", "").strip()
        
        if not from_user_id or not to_user_id:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="from_user_id and to_user_id are required"
            )
        
        # Check both users exist
        from_user = db_session.query(User).filter(User.id == from_user_id).one_or_none()
        to_user = db_session.query(User).filter(User.id == to_user_id).one_or_none()
        
        if not from_user or not to_user:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="One or both users do not exist"
            )
        
        # Get all projects owned by from_user
        projects = db_session.query(ProjectDirectory).filter(
            ProjectDirectory.owner_id == from_user_id
        ).all()
        
        # Transfer each project
        now = datetime.now(timezone.utc)
        for project in projects:
            project.owner_id = to_user_id
            project.updated_at = now
            
            # Record audit event
            audit = AuditEvent(
                actor_user_id=user_id,
                action="transfer_ownership",
                resource_type="project",
                resource_id=project.id,
                details=f"bulk transfer from {from_user_id} to {to_user_id}",
            )
            db_session.add(audit)
        
        db_session.commit()
        
        return jsonify({
            "status": "transferred",
            "projects_count": len(projects)
        })
    finally:
        db_session.remove()
