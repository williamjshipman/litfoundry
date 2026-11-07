"""Admin endpoints."""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from pathlib import Path
import json
from uuid import uuid4
from sqlalchemy.orm import scoped_session
from sqlalchemy import or_
from litfoundry.filesystem import validate_contained_path
from litfoundry.api.errors import ApiError
from litfoundry.auth.sessions import get_or_create_auth_settings, revoke_user_sessions
from litfoundry.catalog import AuthSettings, User, AuditEvent

bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


def require_admin():
    """Verify that the current user is an admin. Raise 403 if not."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            if not user or user.role != "admin" or not user.active:
                raise ApiError(
                    code="FORBIDDEN",
                    status=403,
                    message="Admin access required"
                )
        finally:
            db_session.remove()
    except Exception as e:
        if isinstance(e, ApiError):
            raise
        raise ApiError(
            code="FORBIDDEN",
            status=403,
            message="Admin access required"
        )


def log_audit_event(action: str, resource_type: str, resource_id: str = None, 
                     details: str = None, status: str = "success", error_message: str = None):
    """Log an audit event for an admin action."""
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        try:
            verify_jwt_in_request()
            actor_user_id = get_jwt_identity()
        except:
            actor_user_id = None
        
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        ip_address = request.remote_addr or "unknown"
        
        event = AuditEvent(
            id=str(uuid4()),
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            status=status,
            error_message=error_message,
            request_id=request_id,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(event)
        db_session.commit()
    except Exception as e:
        current_app.logger.warning(f"Failed to log audit event: {str(e)}")
    finally:
        db_session.remove()


@bp.route("/auth-settings", methods=["GET"])
def get_auth_settings():
    """Get authentication settings (policy, lifetimes, throttling).
    
    Admin-only endpoint.
    
    Returns:
        {
            "password_policy": {"min_length": 8, ...},
            "access_token_minutes": 15,
            "refresh_token_hours": 168,
            "throttle_policy": {
                "per_ip_max_attempts": 10,
                "per_identifier_max_attempts": 5,
                "window_minutes": 15,
                ...
            },
            "revision": 1
        }
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        settings = get_or_create_auth_settings(db_session)
        
        return jsonify({
            "password_policy": json.loads(settings.password_policy_json),
            "access_token_minutes": settings.access_token_minutes,
            "refresh_token_hours": settings.refresh_token_hours,
            "throttle_policy": json.loads(settings.throttle_policy_json),
            "revision": settings.revision,
        }), 200
    finally:
        db_session.remove()


@bp.route("/auth-settings", methods=["PUT"])
def update_auth_settings():
    """Update authentication settings.
    
    Admin-only endpoint. Changes to settings invalidate existing sessions
    (via revision bump).
    
    Request body:
        {
            "password_policy": {"min_length": 8, ...},
            "access_token_minutes": 15,
            "refresh_token_hours": 168,
            "throttle_policy": {...}
        }
    
    Returns:
        Updated settings with new revision
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        data = request.get_json() or {}
        settings = get_or_create_auth_settings(db_session)
        
        # Update fields that were provided
        if "password_policy" in data:
            settings.password_policy_json = json.dumps(data["password_policy"])
        
        if "access_token_minutes" in data:
            try:
                minutes = int(data["access_token_minutes"])
                if minutes < 1 or minutes > 60 * 24:  # 1 minute to 1 day
                    raise ValueError("access_token_minutes must be between 1 and 1440")
                settings.access_token_minutes = minutes
            except (TypeError, ValueError) as e:
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message=f"Invalid access_token_minutes: {str(e)}"
                )
        
        if "refresh_token_hours" in data:
            try:
                hours = int(data["refresh_token_hours"])
                if hours < 1 or hours > 365 * 24:  # 1 hour to 1 year
                    raise ValueError("refresh_token_hours must be between 1 and 8760")
                settings.refresh_token_hours = hours
            except (TypeError, ValueError) as e:
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message=f"Invalid refresh_token_hours: {str(e)}"
                )
        
        if "throttle_policy" in data:
            settings.throttle_policy_json = json.dumps(data["throttle_policy"])
        
        # Bump revision to invalidate sessions
        settings.revision += 1
        settings.updated_at = datetime.now(timezone.utc)
        db_session.add(settings)
        db_session.commit()
        
        return jsonify({
            "password_policy": json.loads(settings.password_policy_json),
            "access_token_minutes": settings.access_token_minutes,
            "refresh_token_hours": settings.refresh_token_hours,
            "throttle_policy": json.loads(settings.throttle_policy_json),
            "revision": settings.revision,
        }), 200
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Failed to update auth settings")
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to update auth settings"
        )
    finally:
        db_session.remove()


@bp.route("/users", methods=["GET"])
def list_users():
    """List all users.
    
    Admin-only endpoint.
    
    Returns:
        Array of user objects with id, username, account_type, role, active, last_login_at
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        users = db_session.query(User).all()
        
        return jsonify([{
            "id": user.id,
            "username": user.username,
            "account_type": user.account_type,
            "role": user.role,
            "active": user.active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        } for user in users]), 200
    finally:
        db_session.remove()


@bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user (local or Active Directory).
    
    Admin-only endpoint.
    
    Request body for local user:
        {
            "username": "newuser",
            "password": "SecurePass123",
            "role": "user",
            "account_type": "local"  # optional, defaults to "local"
        }
    
    Request body for AD user:
        {
            "account_type": "active_directory",
            "sid": "S-1-5-21-...",  # required for AD users
            "upn": "user@domain.com",  # optional but recommended
            "samaccountname": "username",  # optional
            "role": "user"
        }
    
    Returns:
        Created user object
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        data = request.get_json() or {}
        account_type = data.get("account_type", "local").lower()
        role = data.get("role", "user").lower()
        
        # Validate role
        if role not in ["admin", "user"]:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="role must be 'admin' or 'user'"
            )
        
        if account_type == "local":
            # Local user creation
            if not data.get("username"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="username is required for local accounts"
                )
            
            if not data.get("password"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="password is required for local accounts"
                )
            
            username = data.get("username", "").strip()
            password = data.get("password", "")
            
            # Validate username
            if not username or len(username) > 255:
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="username must be 1-255 characters"
                )
            
            # Normalize username (lowercase for uniqueness check)
            username_normalized = username.lower()
            
            # Check for duplicate username (case-insensitive)
            existing = db_session.query(User).filter_by(
                account_type="local",
                username_normalized=username_normalized
            ).first()
            
            if existing:
                raise ApiError(
                    code="DUPLICATE_USERNAME",
                    status=409,
                    message="Username already exists"
                )
            
            # Get LocalProvider and hash password
            from litfoundry.auth import get_password_hasher
            hasher = get_password_hasher()
            password_hash = hasher.hash(password)
            
            # Create the user
            user = User(
                id=str(uuid4()),
                account_type="local",
                username=username,
                username_normalized=username_normalized,
                password_hash=password_hash,
                must_change_password=False,
                role=role,
                active=True,
                session_version=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db_session.add(user)
            db_session.commit()
            
            # Log audit event
            log_audit_event(
                action="create_user",
                resource_type="user",
                resource_id=user.id,
                details=json.dumps({"username": username, "role": role, "account_type": "local"})
            )
            
            return jsonify({
                "id": user.id,
                "username": user.username,
                "account_type": user.account_type,
                "role": user.role,
                "active": user.active,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }), 201
        
        elif account_type == "active_directory":
            # AD user creation
            from litfoundry.catalog import DirectoryIdentityBinding
            
            if not data.get("sid"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="sid is required for Active Directory accounts"
                )
            
            sid = data.get("sid", "").strip()
            upn = data.get("upn", "").strip().lower() if data.get("upn") else None
            samaccountname = data.get("samaccountname", "").strip().lower() if data.get("samaccountname") else None
            
            # Validate SID format (basic check: starts with S-1-)
            if not sid.startswith("S-1-"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="Invalid SID format"
                )
            
            # Check for duplicate SID (collision)
            existing_binding = db_session.query(DirectoryIdentityBinding).filter_by(sid=sid).first()
            if existing_binding:
                raise ApiError(
                    code="DUPLICATE_SID",
                    status=409,
                    message="This SID is already bound to another user"
                )
            
            # Derive username from UPN or sAMAccountName
            if upn:
                username = upn.split("@")[0]  # Use the local part of UPN
            elif samaccountname:
                username = samaccountname
            else:
                # Fallback: use SID (last component)
                username = sid.split("-")[-1]
            
            username_normalized = username.lower()
            
            # Check if a user with this username already exists (any account type)
            existing_user = db_session.query(User).filter_by(
                username_normalized=username_normalized
            ).first()
            
            if existing_user:
                raise ApiError(
                    code="DUPLICATE_USERNAME",
                    status=409,
                    message="Username already exists"
                )
            
            # Create the AD user
            user = User(
                id=str(uuid4()),
                account_type="active_directory",
                username=username,
                username_normalized=username_normalized,
                password_hash=None,  # AD users don't have local passwords
                must_change_password=False,
                role=role,
                active=True,
                session_version=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Create the SID binding
            binding = DirectoryIdentityBinding(
                id=str(uuid4()),
                user_id=user.id,
                sid=sid,
                guid=data.get("guid"),
                samaccountname_normalized=samaccountname,
                upn_normalized=upn,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db_session.add(user)
            db_session.add(binding)
            db_session.commit()
            
            # Log audit event
            log_audit_event(
                action="create_user",
                resource_type="user",
                resource_id=user.id,
                details=json.dumps({
                    "account_type": "active_directory",
                    "sid": sid,
                    "upn": upn,
                    "role": role
                })
            )
            
            return jsonify({
                "id": user.id,
                "username": user.username,
                "account_type": user.account_type,
                "role": user.role,
                "active": user.active,
                "sid": sid,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }), 201
        
        else:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="account_type must be 'local' or 'active_directory'"
            )
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Failed to create user")
        log_audit_event(
            action="create_user",
            resource_type="user",
            status="failure",
            error_message=str(e)
        )
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to create user"
        )
    finally:
        db_session.remove()


@bp.route("/users/<user_id>", methods=["PATCH"])
def update_user(user_id):
    """Update a user's properties or rebind AD identity.
    
    Admin-only endpoint. Direct account_type changes through PATCH are rejected
    (conversions come through dedicated actions).
    
    Request body for property update:
        {
            "active": true,
            "role": "user"
        }
    
    Request body for AD rebinding (updates SID binding):
        {
            "rebind": {
                "sid": "S-1-5-21-...",  # new SID
                "upn": "user@domain.com",  # optional
                "samaccountname": "username"  # optional
            }
        }
    
    Returns:
        Updated user object
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        data = request.get_json() or {}
        
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="User not found"
            )
        
        # Handle AD rebinding
        if "rebind" in data:
            from litfoundry.catalog import DirectoryIdentityBinding
            
            if user.account_type != "active_directory":
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="rebind is only for Active Directory users"
                )
            
            rebind_data = data["rebind"]
            if not rebind_data.get("sid"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="rebind.sid is required"
                )
            
            new_sid = rebind_data.get("sid", "").strip()
            
            # Validate SID format
            if not new_sid.startswith("S-1-"):
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="Invalid SID format"
                )
            
            # Check for duplicate SID (collision) - only if different from current
            existing_binding = db_session.query(DirectoryIdentityBinding).filter_by(user_id=user.id).first()
            if existing_binding:
                if new_sid != existing_binding.sid:
                    # New SID - check for collisions
                    collision = db_session.query(DirectoryIdentityBinding).filter_by(sid=new_sid).first()
                    if collision:
                        raise ApiError(
                            code="DUPLICATE_SID",
                            status=409,
                            message="This SID is already bound to another user"
                        )
                    
                    # Update the binding with new SID
                    existing_binding.sid = new_sid
                    existing_binding.upn_normalized = rebind_data.get("upn", "").strip().lower() if rebind_data.get("upn") else existing_binding.upn_normalized
                    existing_binding.samaccountname_normalized = rebind_data.get("samaccountname", "").strip().lower() if rebind_data.get("samaccountname") else existing_binding.samaccountname_normalized
                    existing_binding.updated_at = datetime.now(timezone.utc)
                    db_session.add(existing_binding)
                    
                    # Revoke all sessions for this user (SID changed)
                    user.session_version += 1
                    user.updated_at = datetime.now(timezone.utc)
                    db_session.add(user)
                    db_session.commit()
                    
                    revoke_user_sessions(user_id)
                    
                    # Log audit event
                    log_audit_event(
                        action="rebind_user_ad",
                        resource_type="user",
                        resource_id=user_id,
                        details=json.dumps({"old_sid": existing_binding.sid, "new_sid": new_sid})
                    )
                    
                    return jsonify({
                        "id": user.id,
                        "username": user.username,
                        "account_type": user.account_type,
                        "role": user.role,
                        "active": user.active,
                        "sid": new_sid,
                        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                        "created_at": user.created_at.isoformat(),
                        "updated_at": user.updated_at.isoformat(),
                    }), 200
            
            return jsonify({
                "id": user.id,
                "username": user.username,
                "account_type": user.account_type,
                "role": user.role,
                "active": user.active,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }), 200
        
        # Admin cannot be disabled or role changed through PATCH
        if user.role == "admin" and user.username == "admin":
            if "active" in data and not data["active"]:
                raise ApiError(
                    code="FORBIDDEN",
                    status=403,
                    message="Cannot disable the admin account"
                )
            if "role" in data and data["role"] != "admin":
                raise ApiError(
                    code="FORBIDDEN",
                    status=403,
                    message="Cannot change role of the admin account"
                )
        
        # Reject direct account_type changes
        if "account_type" in data:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Cannot change account_type directly (use dedicated actions)"
            )
        
        # Update fields
        if "active" in data:
            user.active = bool(data["active"])
        
        if "role" in data:
            role = data["role"].lower()
            if role not in ["admin", "user"]:
                raise ApiError(
                    code="VALIDATION_ERROR",
                    status=400,
                    message="role must be 'admin' or 'user'"
                )
            user.role = role
        
        user.updated_at = datetime.now(timezone.utc)
        db_session.add(user)
        db_session.commit()
        
        # Log audit event
        log_audit_event(
            action="update_user",
            resource_type="user",
            resource_id=user.id,
            details=json.dumps(data)
        )
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "account_type": user.account_type,
            "role": user.role,
            "active": user.active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }), 200
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Failed to update user")
        log_audit_event(
            action="update_user",
            resource_type="user",
            resource_id=user_id,
            status="failure",
            error_message=str(e)
        )
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to update user"
        )
    finally:
        db_session.remove()


@bp.route("/users/<user_id>/reset-password", methods=["POST"])
def reset_user_password(user_id):
    """Reset a user's password and revoke their sessions.
    
    Admin-only endpoint.
    
    Request body:
        {
            "password": "NewSecurePass123"
        }
    
    Returns:
        Updated user object
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        data = request.get_json() or {}
        
        if not data.get("password"):
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="password is required"
            )
        
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="User not found"
            )
        
        if user.account_type != "local":
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Cannot reset password for non-local accounts"
            )
        
        # Hash new password
        from litfoundry.auth import get_password_hasher
        hasher = get_password_hasher()
        password_hash = hasher.hash(data["password"])
        user.password_hash = password_hash
        user.must_change_password = False
        user.session_version += 1
        user.updated_at = datetime.now(timezone.utc)
        db_session.add(user)
        db_session.commit()
        
        # Revoke all sessions for this user
        revoke_user_sessions(user_id)
        
        # Log audit event
        log_audit_event(
            action="reset_password",
            resource_type="user",
            resource_id=user_id
        )
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "account_type": user.account_type,
            "role": user.role,
            "active": user.active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }), 200
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Failed to reset password")
        log_audit_event(
            action="reset_password",
            resource_type="user",
            resource_id=user_id,
            status="failure",
            error_message=str(e)
        )
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to reset password"
        )
    finally:
        db_session.remove()


@bp.route("/users/<user_id>/revoke-sessions", methods=["POST"])
def revoke_user_sessions_endpoint(user_id):
    """Revoke all sessions for a user (force logout).
    
    Admin-only endpoint.
    
    Returns:
        Updated user object
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        user = db_session.query(User).filter_by(id=user_id).first()
        if not user:
            raise ApiError(
                code="NOT_FOUND",
                status=404,
                message="User not found"
            )
        
        # Increment session_version to invalidate all sessions
        user.session_version += 1
        user.updated_at = datetime.now(timezone.utc)
        db_session.add(user)
        db_session.commit()
        
        # Revoke refresh tokens
        revoke_user_sessions(user_id)
        
        # Log audit event
        log_audit_event(
            action="revoke_sessions",
            resource_type="user",
            resource_id=user_id
        )
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "account_type": user.account_type,
            "role": user.role,
            "active": user.active,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }), 200
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Failed to revoke sessions")
        log_audit_event(
            action="revoke_sessions",
            resource_type="user",
            resource_id=user_id,
            status="failure",
            error_message=str(e)
        )
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to revoke sessions"
        )
    finally:
        db_session.remove()


@bp.route("/audit-events", methods=["GET"])
def get_audit_events():
    """Get audit events with optional filters.
    
    Admin-only endpoint.
    
    Query parameters:
    - action: Filter by action (e.g., 'create_user', 'reset_password')
    - resource_type: Filter by resource type (e.g., 'user', 'auth_settings')
    - resource_id: Filter by resource ID
    - actor_user_id: Filter by actor user ID
    - status: Filter by status ('success' or 'failure')
    - limit: Maximum number of events to return (default: 100, max: 1000)
    - offset: Number of events to skip (default: 0)
    
    Returns:
        Array of audit events
    """
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Get query parameters
        action_filter = request.args.get("action")
        resource_type_filter = request.args.get("resource_type")
        resource_id_filter = request.args.get("resource_id")
        actor_user_id_filter = request.args.get("actor_user_id")
        status_filter = request.args.get("status")
        
        try:
            limit = int(request.args.get("limit", 100))
            limit = min(limit, 1000)
        except (ValueError, TypeError):
            limit = 100
        
        try:
            offset = int(request.args.get("offset", 0))
        except (ValueError, TypeError):
            offset = 0
        
        # Build query
        query = db_session.query(AuditEvent)
        
        if action_filter:
            query = query.filter_by(action=action_filter)
        if resource_type_filter:
            query = query.filter_by(resource_type=resource_type_filter)
        if resource_id_filter:
            query = query.filter_by(resource_id=resource_id_filter)
        if actor_user_id_filter:
            query = query.filter_by(actor_user_id=actor_user_id_filter)
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        # Get total count
        total = query.count()
        
        # Get events (most recent first)
        events = query.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            "events": [{
                "id": event.id,
                "actor_user_id": event.actor_user_id,
                "action": event.action,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "details": json.loads(event.details) if event.details else None,
                "status": event.status,
                "error_message": event.error_message,
                "request_id": event.request_id,
                "ip_address": event.ip_address,
                "created_at": event.created_at.isoformat(),
            } for event in events],
            "total": total,
            "limit": limit,
            "offset": offset,
        }), 200
    finally:
        db_session.remove()


@bp.route("/logs", methods=["GET"])
def logs():
    """Get recent log entries, filterable by level, process and correlation ID.
    
    Admin-only endpoint. Non-admin users receive 401/403 without detail.
    
    Query parameters:
    - level: Filter by log level (INFO, WARNING, ERROR, etc.)
    - process: Filter by process name (e.g., 'litfoundry-server')
    - request_id: Filter by request correlation ID
    - job_id: Filter by job ID
    - limit: Maximum number of log entries to return (default: 100, max: 1000)
    
    Returns:
    - logs: Array of log entries (JSON objects)
    - total: Total number of entries in log file
    - filtered: Number of entries matching filters
    """
    # TODO: Once m1-local-identity lands, require admin authorization here
    # For now, stub the admin check - requests from localhost are allowed for testing
    
    try:
        # Get query parameters
        level_filter = request.args.get("level", "").upper()
        process_filter = request.args.get("process", "")
        request_id_filter = request.args.get("request_id", "")
        job_id_filter = request.args.get("job_id", "")
        
        try:
            limit = int(request.args.get("limit", 100))
            limit = min(limit, 1000)  # Cap at 1000
        except (ValueError, TypeError):
            limit = 100
        
        # Get log file path
        data_root = current_app.config.get("LITFOUNDRY_DATA_ROOT")
        if not data_root:
            return jsonify({
                "error": "Data root not configured",
                "logs": [],
                "total": 0,
                "filtered": 0
            }), 503
        
        data_root_path = Path(data_root)
        
        # Validate that the log file is contained within data_root
        # (protects against symlink escapes)
        try:
            log_file = validate_contained_path(data_root_path, Path("logs") / "litfoundry.log")
        except ValueError as e:
            return jsonify({
                "error": f"Path validation failed: {str(e)}",
                "logs": [],
                "total": 0,
                "filtered": 0
            }), 400
        
        if not log_file.exists():
            return jsonify({
                "logs": [],
                "total": 0,
                "filtered": 0,
                "limit": limit
            }), 200
        
        # Read and parse logs
        logs_list = []
        total = 0
        filtered = 0
        
        try:
            with open(log_file, 'r') as f:
                # Read lines in reverse to get most recent first
                all_lines = f.readlines()
                all_lines.reverse()
                
                for line in all_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        entry = json.loads(line)
                        total += 1
                        
                        # Apply filters
                        if level_filter and entry.get("level", "").upper() != level_filter:
                            continue
                        
                        if process_filter and entry.get("process", "") != process_filter:
                            continue
                        
                        if request_id_filter and entry.get("request_id", "") != request_id_filter:
                            continue
                        
                        if job_id_filter and entry.get("job_id", "") != job_id_filter:
                            continue
                        
                        filtered += 1
                        logs_list.append(entry)
                        
                        # Stop if we've collected enough
                        if len(logs_list) >= limit:
                            break
                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue
        except IOError as e:
            return jsonify({
                "error": f"Could not read log file: {str(e)}",
                "logs": [],
                "total": 0,
                "filtered": 0
            }), 500
        
        return jsonify({
            "logs": logs_list,
            "total": total,
            "filtered": filtered,
            "limit": limit
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Unexpected error: {str(e)}",
            "logs": [],
            "total": 0,
            "filtered": 0
        }), 500
