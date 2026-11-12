"""Active Directory user revalidation logic.

Periodic revalidation checks each AD user's account state and revokes sessions
if the account is disabled, locked, deleted, or has changed SID.

This module encapsulates the revalidation logic and will be integrated with
the background job framework (m2-background-jobs) once it is available.
"""

import logging
from datetime import datetime, timezone
from sqlalchemy import and_
from sqlalchemy.orm import Session

from litfoundry.catalog import DirectoryConfig, DirectoryIdentityBinding, User
from litfoundry.directory import DirectoryClient
from litfoundry.directory.client import escape_filter_chars

logger = logging.getLogger(__name__)


def run_ad_revalidation(db_session: Session) -> dict:
    """Run periodic revalidation of all active AD-bound users.
    
    Checks each user's account state in the directory:
    - If disabled, locked, deleted, or SID changed: revoke sessions via session_version
    - Update last_directory_success_at on successful domain contact
    
    Returns:
        dict with keys:
            - total_users: number of AD users checked
            - revoked_count: number of users who had sessions revoked
            - errors: list of error messages
    """
    result = {
        "total_users": 0,
        "revoked_count": 0,
        "errors": [],
    }
    
    try:
        # Get AD configuration
        ad_config = db_session.query(DirectoryConfig).filter_by(id=1).first()
        if not ad_config or not ad_config.enabled:
            logger.info("AD revalidation: AD not configured or disabled")
            return result
        
        # Connect to directory as service account
        client = DirectoryClient(
            domain_name=ad_config.domain_name,
            domain_controllers=ad_config.domain_controllers,
            base_dn=ad_config.base_dn,
            tls_mode=ad_config.tls_mode,
            ca_bundle_pem=ad_config.ca_bundle_pem,
            connect_timeout=ad_config.connection_timeout,
            read_timeout=ad_config.read_timeout,
        )
        
        try:
            # Get all active AD users with bindings
            ad_users = (
                db_session.query(User, DirectoryIdentityBinding)
                .join(DirectoryIdentityBinding, User.id == DirectoryIdentityBinding.user_id)
                .filter(
                    and_(
                        User.account_type == "active_directory",
                        User.active == True,
                    )
                )
                .all()
            )
            
            result["total_users"] = len(ad_users)
            
            for user, binding in ad_users:
                try:
                    # Search for the user in AD
                    search_filter = f"(sAMAccountName={escape_filter_chars(binding.samaccountname_normalized)})"
                    
                    results = client.connect_and_search(
                        username=ad_config.service_account_username,
                        password=ad_config.service_account_password,
                        search_filter=search_filter,
                    )
                    
                    if not results:
                        # User deleted in AD - revoke sessions
                        logger.warning(
                            f"AD user revocation: {user.id} deleted in directory",
                            extra={"user_id": user.id, "reason": "deleted"},
                        )
                        user.session_version += 1
                        db_session.add(user)
                        result["revoked_count"] += 1
                        continue
                    
                    # Get the user object
                    user_entry = results[0]
                    
                    # Check SID - if changed, revoke
                    new_sid = user_entry.get("objectSid")
                    if new_sid and new_sid != binding.sid:
                        logger.warning(
                            f"AD user revocation: {user.id} SID changed",
                            extra={"user_id": user.id, "reason": "sid_changed"},
                        )
                        user.session_version += 1
                        db_session.add(user)
                        result["revoked_count"] += 1
                        continue
                    
                    # Check account state flags
                    user_account_control = user_entry.get("userAccountControl")
                    computed_uac = user_entry.get("msDS-User-Account-Control-Computed")
                    
                    # Check if disabled (bit 1 in userAccountControl)
                    if user_account_control and (user_account_control & 0x0002):
                        logger.warning(
                            f"AD user revocation: {user.id} disabled in directory",
                            extra={"user_id": user.id, "reason": "disabled"},
                        )
                        user.session_version += 1
                        db_session.add(user)
                        result["revoked_count"] += 1
                        continue
                    
                    # Check if locked (bit 4 in msDS-User-Account-Control-Computed)
                    if computed_uac and (computed_uac & 0x0010):
                        logger.warning(
                            f"AD user revocation: {user.id} locked in directory",
                            extra={"user_id": user.id, "reason": "locked"},
                        )
                        user.session_version += 1
                        db_session.add(user)
                        result["revoked_count"] += 1
                        continue
                
                except Exception as e:
                    result["errors"].append(f"Error checking user {user.id}: {str(e)}")
                    logger.exception(f"Error revalidating user {user.id}")
                    continue
            
            # Update last_directory_success_at
            ad_config.last_directory_success_at = datetime.now(timezone.utc)
            db_session.add(ad_config)
            db_session.commit()
            
            logger.info(
                f"AD revalidation completed: {result['total_users']} users, "
                f"{result['revoked_count']} revoked",
                extra={
                    "total_users": result["total_users"],
                    "revoked_count": result["revoked_count"],
                },
            )
        
        finally:
            try:
                client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from directory: {e}")
    
    except Exception as e:
        result["errors"].append(f"Revalidation failed: {str(e)}")
        logger.exception("AD revalidation failed")
    
    return result
