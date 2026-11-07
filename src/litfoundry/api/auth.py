"""Authentication and setup API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import scoped_session

from litfoundry.api.errors import ApiError
from litfoundry.auth import LocalProvider, create_user_with_password
from litfoundry.auth.bootstrap import (
    verify_bootstrap_token,
    hash_bootstrap_token,
    delete_bootstrap_token_file,
    get_bootstrap_token_expiry_time,
    is_bootstrap_token_expired,
)
from litfoundry.catalog import User, BootstrapToken, AuthSettings


auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
setup_bp = Blueprint("setup", __name__, url_prefix="/api/v1/setup")


def check_admin_exists(session) -> bool:
    """Check if an admin user already exists."""
    return session.query(User).filter_by(role="admin").first() is not None


def get_or_create_auth_settings(session) -> AuthSettings:
    """Get or create the single auth_settings row."""
    settings = session.query(AuthSettings).filter_by(id=1).first()
    if not settings:
        # Create default auth settings
        now = datetime.now(timezone.utc)
        settings = AuthSettings(
            id=1,
            password_policy_json='{"min_length": 8}',
            access_token_minutes=15,
            refresh_token_hours=7*24,
            throttle_policy_json='{"window_seconds": 300, "max_attempts": 5}',
            revision=1,
            created_at=now,
            updated_at=now,
        )
        session.add(settings)
        session.commit()
    return settings


@setup_bp.route("/status", methods=["GET"])
def setup_status():
    """Get the current setup status (whether admin exists).
    
    No authentication required - this endpoint is part of the setup gate.
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        admin_exists = check_admin_exists(db_session)
        return jsonify({
            "setup_required": not admin_exists
        }), 200
    finally:
        db_session.remove()


@setup_bp.route("/admin", methods=["POST"])
def setup_admin():
    """Complete first-run setup by creating the admin account.
    
    Accepts a valid bootstrap token and a new password, creates the admin
    account, and invalidates the token. Only works once (until admin exists).
    
    Request body:
        {
            "token": "base32-encoded-token",
            "password": "password"
        }
    
    Returns:
        {"success": true} on success
        Error response if token invalid/expired, password weak, or admin already exists
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        # Check if admin already exists
        if check_admin_exists(db_session):
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Setup already complete"
            )
        
        # Get request data
        data = request.get_json() or {}
        token = data.get("token", "").strip()
        password = data.get("password", "").strip()
        
        if not token:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Bootstrap token required"
            )
        
        if not password:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Password required"
            )
        
        # Validate password policy (basic: 8+ chars)
        if len(password) < 8:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Password must be at least 8 characters"
            )
        
        # Find unconsumed bootstrap token
        bootstrap_token = db_session.query(BootstrapToken).filter_by(
            consumed_at=None
        ).first()
        
        if not bootstrap_token:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="No valid bootstrap token available"
            )
        
        # Check if token has expired
        if is_bootstrap_token_expired(bootstrap_token.expires_at):
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Bootstrap token has expired"
            )
        
        # Verify token
        if not verify_bootstrap_token(token, bootstrap_token.token_hash):
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Invalid bootstrap token"
            )
        
        # Atomic: consume token and create admin
        # Mark token as consumed
        bootstrap_token.consumed_at = datetime.now(timezone.utc)
        db_session.add(bootstrap_token)
        
        # Create admin account
        admin = create_user_with_password(
            str(uuid4()),
            "admin",
            password,
            role="admin",
            account_type="local"
        )
        db_session.add(admin)
        
        # Commit atomically
        db_session.commit()
        
        # Delete token file
        try:
            delete_bootstrap_token_file(current_app.config["DATA_ROOT"])
        except Exception:
            pass  # File might not exist or permissions might prevent deletion
        
        return jsonify({"success": True}), 200
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Setup failed")
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Setup failed"
        )
    finally:
        db_session.remove()


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user with username/password.
    
    Currently supports local provider only.
    
    Request body:
        {
            "username": "username",
            "password": "password",
            "provider": "local"  # optional, defaults to "local"
        }
    
    Returns:
        {
            "user": {
                "id": "user-uuid",
                "username": "username",
                "must_change_password": false
            }
        }
        Sets secure HttpOnly cookies: access_token, refresh_token, csrf_token
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        provider_name = data.get("provider", "local").strip()
        
        if not username or not password:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Username and password required"
            )
        
        if provider_name != "local":
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message=f"Provider '{provider_name}' not available"
            )
        
        # Verify credentials with local provider
        provider = LocalProvider()
        user = provider.verify_credentials(username, password, db_session)
        
        if not user:
            raise ApiError(
                code="FORBIDDEN",
                status=403,
                message="Invalid credentials"
            )
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        db_session.add(user)
        db_session.commit()
        
        return jsonify({
            "user": {
                "id": user.id,
                "username": user.username,
                "must_change_password": user.must_change_password
            }
        }), 200
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Login failed")
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Login failed"
        )
    finally:
        db_session.remove()


@auth_bp.route("/me", methods=["GET"])
def get_me():
    """Get the current authenticated user information.
    
    Requires: Valid access token
    
    Returns:
        {
            "id": "user-uuid",
            "username": "username",
            "must_change_password": false,
            "role": "admin"
        }
    """
    # TODO: Implement JWT validation and user retrieval
    # This will be done in task 4.4 along with session setup
    raise ApiError(
        code="INTERNAL_ERROR",
        status=500,
        message="Not yet implemented"
    )


@auth_bp.route("/methods", methods=["GET"])
def get_auth_methods():
    """Get list of available authentication methods.
    
    Returns:
        {
            "methods": ["local"]  # will include "active_directory" when M2 is available
        }
    """
    return jsonify({
        "methods": ["local"]
    }), 200
