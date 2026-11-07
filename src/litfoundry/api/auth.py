"""Authentication and setup API endpoints."""

import json
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
from litfoundry.auth.throttling import ThrottlingPolicy, LoginThrottler
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
        # Default throttling policy: 10 attempts per IP per 15 minutes, 5 per username per 15 minutes
        throttle_policy = {
            "per_ip_max_attempts": 10,
            "per_identifier_max_attempts": 5,
            "window_minutes": 15,
            "backoff_base_seconds": 1.0,
            "backoff_max_seconds": 900,  # 15 minutes
        }
        settings = AuthSettings(
            id=1,
            password_policy_json='{"min_length": 8}',
            access_token_minutes=15,
            refresh_token_hours=7*24,
            throttle_policy_json=json.dumps(throttle_policy),
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
    
    Supports local and active_directory providers.
    
    Request body:
        {
            "username": "username",
            "password": "password",
            "provider": "local"  # optional, defaults to "local"; can also be "active_directory"
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
        
        # Get client IP address (handle proxies)
        client_ip = request.remote_addr or "unknown"
        if request.headers.get("X-Forwarded-For"):
            client_ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
        
        if not username or not password:
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message="Username and password required"
            )
        
        # Validate provider
        if provider_name not in ("local", "active_directory"):
            raise ApiError(
                code="VALIDATION_ERROR",
                status=400,
                message=f"Provider '{provider_name}' not available"
            )
        
        # Get auth settings and set up throttling
        auth_settings = get_or_create_auth_settings(db_session)
        throttle_policy_dict = json.loads(auth_settings.throttle_policy_json)
        
        ip_policy = ThrottlingPolicy(
            max_attempts=throttle_policy_dict.get("per_ip_max_attempts", 10),
            window_minutes=throttle_policy_dict.get("window_minutes", 15),
            backoff_base_seconds=throttle_policy_dict.get("backoff_base_seconds", 1.0),
            backoff_max_seconds=throttle_policy_dict.get("backoff_max_seconds", 900),
        )
        
        # For AD throttling, use 3 per identifier per 15 minutes
        ad_identifier_policy = ThrottlingPolicy(
            max_attempts=3,
            window_minutes=15,
            backoff_base_seconds=throttle_policy_dict.get("backoff_base_seconds", 1.0),
            backoff_max_seconds=throttle_policy_dict.get("backoff_max_seconds", 900),
        )
        
        identifier_policy = ThrottlingPolicy(
            max_attempts=throttle_policy_dict.get("per_identifier_max_attempts", 5),
            window_minutes=throttle_policy_dict.get("window_minutes", 15),
            backoff_base_seconds=throttle_policy_dict.get("backoff_base_seconds", 1.0),
            backoff_max_seconds=throttle_policy_dict.get("backoff_max_seconds", 900),
        )
        
        throttler = LoginThrottler(ip_policy, identifier_policy)
        ad_throttler = LoginThrottler(ip_policy, ad_identifier_policy)
        
        # Check if admin account exists and if this is an admin login
        admin_user = db_session.query(User).filter_by(role="admin").first()
        is_admin_account = admin_user and admin_user.username.lower().strip() == username.lower().strip()
        
        # Check throttle (admin only checks per-IP, regular users check both)
        # Use AD throttler if provider is AD
        active_throttler = ad_throttler if provider_name == "active_directory" else throttler
        throttle_check = active_throttler.check_throttle(
            db_session, 
            client_ip, 
            identifier=username,
            is_admin=is_admin_account
        )
        
        if throttle_check["throttled"]:
            raise ApiError(
                code="AUTH_THROTTLED",
                status=429,
                message="Too many login attempts. Please try again later.",
                details={"retry_after_seconds": throttle_check["retry_after_seconds"]}
            )
        
        # Select provider and verify credentials
        if provider_name == "active_directory":
            from litfoundry.auth import ActiveDirectoryProvider
            from litfoundry.catalog import DirectoryConfig
            
            # Check if AD is enabled
            ad_config = db_session.query(DirectoryConfig).filter_by(id=1).first()
            if not ad_config or not ad_config.enabled:
                raise ApiError(
                    code="AUTH_PROVIDER_DISABLED",
                    status=403,
                    message="Active Directory authentication is not available"
                )
            
            provider = ActiveDirectoryProvider()
        else:
            provider = LocalProvider()
        
        # Verify credentials
        user = provider.verify_credentials(username, password, db_session)
        
        # Always record the attempt, even on failure (for throttling)
        active_throttler.record_attempt(
            db_session,
            client_ip,
            identifier=username,
            is_admin=is_admin_account
        )
        
        if not user:
            db_session.commit()  # Commit the throttle recording
            # Return generic error message (same for AD and local)
            if provider_name == "active_directory":
                # Could be disabled account, locked account, or wrong password
                # Return generic error to avoid enumeration
                raise ApiError(
                    code="FORBIDDEN",
                    status=403,
                    message="Invalid credentials"
                )
            else:
                raise ApiError(
                    code="FORBIDDEN",
                    status=403,
                    message="Invalid credentials"
                )
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        db_session.add(user)
        db_session.commit()
        
        # Create JWT tokens (include directory_revision claim for AD users)
        from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies
        
        additional_claims = {}
        if provider_name == "active_directory":
            from litfoundry.catalog import DirectoryConfig
            ad_config = db_session.query(DirectoryConfig).filter_by(id=1).first()
            if ad_config:
                additional_claims["directory_revision"] = ad_config.directory_revision
        
        access_token = create_access_token(identity=user.id, additional_claims=additional_claims)
        refresh_token = create_refresh_token(identity=user.id)
        
        response_data = jsonify({
            "user": {
                "id": user.id,
                "username": user.username,
                "must_change_password": user.must_change_password
            }
        })
        
        # Set JWT cookies
        set_access_cookies(response_data, access_token)
        set_refresh_cookies(response_data, refresh_token)
        
        return response_data, 200
    
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


@auth_bp.route("/methods", methods=["GET"])
def get_auth_methods():
    """Get the list of available authentication methods.
    
    No authentication required - this endpoint is part of the sign-in flow.
    
    Returns:
        {
            "methods": [
                {"name": "local", "display_name": "Local Account"},
                {"name": "active_directory", "display_name": "Active Directory"}  # if enabled
            ]
        }
    """
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        from litfoundry.catalog import DirectoryConfig
        
        methods = [
            {"name": "local", "display_name": "Local Account"}
        ]
        
        # Check if AD is enabled
        ad_config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        if ad_config and ad_config.enabled:
            methods.append({
                "name": "active_directory",
                "display_name": "Active Directory"
            })
        
        return jsonify({"methods": methods}), 200
    
    except Exception as e:
        current_app.logger.exception("Failed to get auth methods")
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to get auth methods"
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
            "display_name": "Display Name",
            "must_change_password": false,
            "role": "admin",
            "provider": "local"
        }
    """
    from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
    
    # Verify JWT manually so we can provide better errors
    try:
        verify_jwt_in_request()
    except Exception as e:
        raise ApiError(
            code="UNAUTHENTICATED",
            status=401,
            message="Invalid or missing token"
        )
    
    try:
        jwt_data = get_jwt()
        user_id = jwt_data.get("user_id") or get_jwt_identity()
        
        if not user_id:
            raise ApiError(
                code="UNAUTHENTICATED",
                status=401,
                message="Invalid token"
            )
        
        db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
        try:
            # Check user still exists and is active
            user = db_session.query(User).filter_by(id=user_id).first()
            if not user or not user.active:
                raise ApiError(
                    code="UNAUTHENTICATED",
                    status=401,
                    message="User not found or inactive"
                )
            
            # Revalidate session version and auth settings revision
            user_sv = jwt_data.get("sv")
            if user_sv is not None and user_sv != user.session_version:
                raise ApiError(
                    code="UNAUTHENTICATED",
                    status=401,
                    message="Session invalidated by password change"
                )
            
            auth_settings = get_or_create_auth_settings(db_session)
            user_ar = jwt_data.get("ar")
            if user_ar is not None and user_ar != auth_settings.revision:
                raise ApiError(
                    code="UNAUTHENTICATED",
                    status=401,
                    message="Session invalidated by settings change"
                )
            
            return jsonify({
                "id": user.id,
                "username": user.username,
                "display_name": user.username,  # Can be extended later for full names
                "must_change_password": user.must_change_password,
                "role": user.role,
                "provider": user.account_type,
            }), 200
        finally:
            db_session.remove()
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.exception("Failed to get user info")
        raise ApiError(
            code="INTERNAL_ERROR",
            status=500,
            message="Failed to retrieve user information"
        )
