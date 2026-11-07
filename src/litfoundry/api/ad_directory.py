"""Active Directory admin endpoints."""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from flask import Blueprint, jsonify, current_app, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
import json
from uuid import uuid4
from sqlalchemy.orm import scoped_session
from sqlalchemy import or_

from litfoundry.api.errors import ApiError
from litfoundry.api.admin import require_admin, log_audit_event
from litfoundry.catalog import DirectoryConfig, DirectoryIdentityBinding, User, AuditEvent
from litfoundry.directory import DirectoryClient, DirectoryConnectionError, DirectorySearchError, DirectoryBindError
from litfoundry.secrets import encrypt_secret, decrypt_secret

bp = Blueprint("admin_directory", __name__, url_prefix="/api/v1/admin/ad-directory")


@bp.route("", methods=["GET"])
def get_directory_config():
    """Get the current AD configuration (without password)."""
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        
        if not config:
            return jsonify(None), 200
        
        return jsonify({
            "id": config.id,
            "domain_name": config.domain_name,
            "netbios_name": config.netbios_name,
            "upn_suffixes": json.loads(config.upn_suffixes_json),
            "domain_controllers": json.loads(config.domain_controllers_json),
            "base_dn": config.base_dn,
            "tls_mode": config.tls_mode,
            "connection_timeout_seconds": config.connection_timeout_seconds,
            "read_timeout_seconds": config.read_timeout_seconds,
            "revalidation_interval_minutes": config.revalidation_interval_minutes,
            "grace_period_minutes": config.grace_period_minutes,
            "service_account_username": config.service_account_username,
            "enabled": config.enabled,
            "last_test_passed_revision": config.last_test_passed_revision,
            "last_directory_success_at": config.last_directory_success_at.isoformat() if config.last_directory_success_at else None,
            "directory_revision": config.directory_revision,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
        }), 200
    finally:
        db_session.remove()


@bp.route("", methods=["PUT"])
def set_directory_config():
    """Set or update the AD configuration."""
    require_admin()
    
    data = request.get_json()
    if not data:
        raise ApiError("VALIDATION_ERROR", 400, "Request body required")
    
    # Validate required fields
    required = ["domain_name", "domain_controllers", "base_dn", "tls_mode"]
    for field in required:
        if field not in data:
            raise ApiError("VALIDATION_ERROR", 400, f"Missing required field: {field}")
    
    # Validate TLS mode
    if data.get("tls_mode") not in ("ldaps", "starttls"):
        raise ApiError("VALIDATION_ERROR", 400, "Invalid TLS mode")
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        
        if config:
            config.domain_name = data.get("domain_name", config.domain_name)
            config.netbios_name = data.get("netbios_name", config.netbios_name)
            config.upn_suffixes_json = json.dumps(data.get("upn_suffixes", json.loads(config.upn_suffixes_json)))
            config.domain_controllers_json = json.dumps(data.get("domain_controllers", json.loads(config.domain_controllers_json)))
            config.base_dn = data.get("base_dn", config.base_dn)
            config.tls_mode = data.get("tls_mode", config.tls_mode)
            config.connection_timeout_seconds = data.get("connection_timeout_seconds", config.connection_timeout_seconds)
            config.read_timeout_seconds = data.get("read_timeout_seconds", config.read_timeout_seconds)
            config.revalidation_interval_minutes = data.get("revalidation_interval_minutes", config.revalidation_interval_minutes)
            config.grace_period_minutes = data.get("grace_period_minutes", config.grace_period_minutes)
            config.service_account_username = data.get("service_account_username", config.service_account_username)
            
            # Handle password update (write-only)
            if "service_account_password" in data:
                if data["service_account_password"]:
                    config.service_account_password_encrypted = encrypt_secret(data["service_account_password"])
            
            config.enabled = False  # Require test before enabling
            config.last_test_passed_revision = None
            config.directory_revision += 1  # Increment revision on change
            config.updated_at = datetime.now(timezone.utc)
        else:
            # Create new config
            ca_bundle_pem = None
            if "ca_bundle_pem" in data:
                ca_bundle_pem = encrypt_secret(data["ca_bundle_pem"]) if data["ca_bundle_pem"] else None
            
            service_account_password = None
            if "service_account_password" in data:
                service_account_password = encrypt_secret(data["service_account_password"]) if data["service_account_password"] else None
            
            config = DirectoryConfig(
                id=1,
                domain_name=data.get("domain_name"),
                netbios_name=data.get("netbios_name"),
                upn_suffixes_json=json.dumps(data.get("upn_suffixes", [])),
                domain_controllers_json=json.dumps(data.get("domain_controllers", [])),
                base_dn=data.get("base_dn"),
                tls_mode=data.get("tls_mode"),
                ca_bundle_pem_encrypted=ca_bundle_pem,
                connection_timeout_seconds=data.get("connection_timeout_seconds", 30),
                read_timeout_seconds=data.get("read_timeout_seconds", 30),
                revalidation_interval_minutes=data.get("revalidation_interval_minutes", 15),
                grace_period_minutes=data.get("grace_period_minutes", 60),
                service_account_username=data.get("service_account_username"),
                service_account_password_encrypted=service_account_password,
                enabled=False,
                directory_revision=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db_session.add(config)
        
        db_session.commit()
        
        # Log audit event
        log_audit_event(
            "update",
            "directory_config",
            "1",
            f"Updated AD configuration: {data.get('domain_name')}"
        )
        
        return jsonify({"message": "Configuration saved"}), 200
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error setting directory config: {str(e)}")
        raise ApiError("INTERNAL_ERROR", 500, "Failed to save configuration")
    finally:
        db_session.remove()


@bp.route("", methods=["DELETE"])
def delete_directory_config():
    """Delete the AD configuration and revoke AD sessions."""
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        
        if config:
            db_session.delete(config)
            
            # Delete all directory bindings
            db_session.query(DirectoryIdentityBinding).delete()
            
            db_session.commit()
            
            # Log audit event
            log_audit_event(
                "delete",
                "directory_config",
                "1",
                "Deleted AD configuration"
            )
        
        return jsonify({"message": "Configuration deleted"}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting directory config: {str(e)}")
        raise ApiError("INTERNAL_ERROR", 500, "Failed to delete configuration")
    finally:
        db_session.remove()


@bp.route("/test", methods=["POST"])
def test_directory_connection():
    """Test the directory connection and return sanitized results."""
    require_admin()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        
        if not config:
            raise ApiError("VALIDATION_ERROR", 400, "No AD configuration found")
        
        # Validate that service account is configured
        if not config.service_account_username or not config.service_account_password_encrypted:
            raise ApiError("VALIDATION_ERROR", 400, "Service account credentials required")
        
        # Try to create the directory client
        try:
            ca_bundle_path = None
            if config.ca_bundle_pem_encrypted:
                # For now, we'll skip the CA bundle file handling
                # In production, this would write to a temp file
                pass
            
            client = DirectoryClient(
                domain_controllers=json.loads(config.domain_controllers_json),
                base_dn=config.base_dn,
                tls_mode=config.tls_mode,
                ca_bundle_path=ca_bundle_path,
                connection_timeout=config.connection_timeout_seconds,
                read_timeout=config.read_timeout_seconds,
            )
            
            # Decrypt service account password
            service_account_password = decrypt_secret(config.service_account_password_encrypted)
            
            # Try to connect and search
            try:
                result = client.connect_and_search(
                    service_account_dn=config.service_account_username,
                    service_account_password=service_account_password,
                    search_filter="(objectClass=*)",
                    attributes=["cn"],
                )
                
                # Test passed
                config.last_test_passed_revision = config.directory_revision
                config.last_directory_success_at = datetime.now(timezone.utc)
                db_session.commit()
                
                log_audit_event(
                    "test",
                    "directory_config",
                    "1",
                    "Connection test passed"
                )
                
                return jsonify({
                    "success": True,
                    "message": "Directory connection successful"
                }), 200
            
            except (DirectoryConnectionError, DirectorySearchError, DirectoryBindError) as e:
                # Log diagnostic event
                log_audit_event(
                    "directory_check_failed",
                    "directory",
                    details=str(e),
                    status="failure",
                    error_message=str(e)
                )
                
                return jsonify({
                    "success": False,
                    "message": "Connection test failed",
                    "error": str(e)
                }), 400
        
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Failed to create directory client",
                "error": str(e)
            }), 400
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error testing directory connection: {str(e)}")
        raise ApiError("INTERNAL_ERROR", 500, "Failed to test connection")
    finally:
        db_session.remove()


@bp.route("/resolve-user", methods=["POST"])
def resolve_ad_user():
    """Resolve an AD user and return their details."""
    require_admin()
    
    data = request.get_json()
    if not data or "identifier" not in data:
        raise ApiError("VALIDATION_ERROR", 400, "identifier required")
    
    identifier = data.get("identifier", "").strip()
    
    db_session = scoped_session(current_app.config["DB_SESSION_FACTORY"])
    try:
        config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        
        if not config:
            raise ApiError("VALIDATION_ERROR", 400, "No AD configuration found")
        
        if not config.service_account_username or not config.service_account_password_encrypted:
            raise ApiError("VALIDATION_ERROR", 400, "Service account not configured")
        
        # Decrypt service account password
        service_account_password = decrypt_secret(config.service_account_password_encrypted)
        
        # Create directory client
        try:
            client = DirectoryClient(
                domain_controllers=json.loads(config.domain_controllers_json),
                base_dn=config.base_dn,
                tls_mode=config.tls_mode,
                connection_timeout=config.connection_timeout_seconds,
                read_timeout=config.read_timeout_seconds,
            )
            
            # Escape the identifier
            escaped_identifier = DirectoryClient.escape_filter_value(identifier)
            
            # Search for user by sAMAccountName or UPN
            search_filter = f"(|(sAMAccountName={escaped_identifier})(userPrincipalName={escaped_identifier}))"
            
            result = client.connect_and_search(
                service_account_dn=config.service_account_username,
                service_account_password=service_account_password,
                search_filter=search_filter,
            )
            
            # Extract SID from raw bytes if necessary
            sid_value = result["attributes"].get("objectSid")
            if isinstance(sid_value, bytes):
                # Convert bytes to SID string format (this is a simplified conversion)
                # In production, use a proper ldap3 conversion function
                sid_value = str(sid_value)
            
            return jsonify({
                "dn": result["dn"],
                "sAMAccountName": result["attributes"].get("sAMAccountName"),
                "userPrincipalName": result["attributes"].get("userPrincipalName"),
                "displayName": result["attributes"].get("displayName"),
                "objectSid": sid_value,
                "enabled": not (result["attributes"].get("userAccountControl", 0) & 0x2),
            }), 200
        
        except (DirectoryConnectionError, DirectorySearchError, DirectoryBindError) as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400
    
    except ApiError:
        raise
    except Exception as e:
        current_app.logger.error(f"Error resolving AD user: {str(e)}")
        raise ApiError("INTERNAL_ERROR", 500, "Failed to resolve user")
    finally:
        db_session.remove()
