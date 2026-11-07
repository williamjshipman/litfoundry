"""JWT session token management and rotation."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy.orm import Session

from litfoundry.catalog import User, RefreshToken, AuthSettings


def get_or_create_auth_settings(session: Session) -> AuthSettings:
    """Get or create the single auth_settings row."""
    settings = session.query(AuthSettings).filter_by(id=1).first()
    if not settings:
        now = datetime.now(timezone.utc)
        throttle_policy = {
            "per_ip_max_attempts": 10,
            "per_identifier_max_attempts": 5,
            "window_minutes": 15,
            "backoff_base_seconds": 1.0,
            "backoff_max_seconds": 900,
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


def create_token_pair(
    user: User,
    session: Session,
    settings: Optional[AuthSettings] = None,
) -> dict:
    """Create access and refresh token pair with rotation tracking.
    
    Args:
        user: User object
        session: SQLAlchemy session
        settings: AuthSettings (will be fetched if not provided)
        
    Returns:
        Dict with access_token, refresh_token, and additional user info
    """
    if settings is None:
        settings = get_or_create_auth_settings(session)
    
    now = datetime.now(timezone.utc)
    access_expires = timedelta(minutes=settings.access_token_minutes)
    refresh_expires = timedelta(hours=settings.refresh_token_hours)
    
    # Create tokens with additional claims
    family_id = str(uuid4())
    access_jti = str(uuid4())
    refresh_jti = str(uuid4())
    
    additional_claims = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "sv": user.session_version,  # session_version for revalidation
        "ar": settings.revision,  # auth_settings.revision for revalidation
    }
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims={**additional_claims, "jti": access_jti},
        expires_delta=access_expires,
    )
    
    refresh_token = create_refresh_token(
        identity=user.id,
        additional_claims={**additional_claims, "jti": refresh_jti, "family_id": family_id},
        expires_delta=refresh_expires,
    )
    
    # Store refresh token for rotation tracking
    refresh_token_obj = RefreshToken(
        jti=refresh_jti,
        user_id=user.id,
        family_id=family_id,
        expires_at=now + refresh_expires,
        revoked_at=None,
        replaced_by=None,
        created_at=now,
    )
    session.add(refresh_token_obj)
    session.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": int(access_expires.total_seconds()),
    }


def rotate_refresh_token(
    old_jti: str,
    family_id: str,
    user_id: str,
    session: Session,
    settings: Optional[AuthSettings] = None,
) -> tuple:
    """Rotate a refresh token and return new token pair or raise if token was reused.
    
    Implements refresh token rotation with family revocation on reuse detection.
    
    Args:
        old_jti: JTI of the refresh token being used
        family_id: Family ID for token rotation tracking
        user_id: User ID
        session: SQLAlchemy session
        settings: AuthSettings (will be fetched if not provided)
        
    Returns:
        Tuple of (access_token, new_refresh_token)
        
    Raises:
        ValueError: If token was already used (reuse detected) or revoked
    """
    if settings is None:
        settings = get_or_create_auth_settings(session)
    
    # Look up the refresh token
    token_obj = session.query(RefreshToken).filter_by(jti=old_jti).first()
    
    if not token_obj:
        raise ValueError("Refresh token not found")
    
    if token_obj.revoked_at:
        raise ValueError("Refresh token has been revoked")
    
    if token_obj.replaced_by:
        # Token reuse detected - revoke entire family
        now = datetime.now(timezone.utc)
        family_tokens = session.query(RefreshToken).filter_by(family_id=family_id).all()
        for ft in family_tokens:
            if not ft.revoked_at:
                ft.revoked_at = now
        session.commit()
        raise ValueError("Refresh token reuse detected - family revoked")
    
    # Check expiry
    now = datetime.now(timezone.utc)
    expires_at = token_obj.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < now:
        raise ValueError("Refresh token has expired")
    
    # Get user and create new pair
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        raise ValueError("User not found")
    
    # Mark old token as replaced
    new_refresh_jti = str(uuid4())
    token_obj.replaced_by = new_refresh_jti
    session.add(token_obj)
    
    # Create new token in same family
    access_expires = timedelta(minutes=settings.access_token_minutes)
    refresh_expires = timedelta(hours=settings.refresh_token_hours)
    
    additional_claims = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "sv": user.session_version,
        "ar": settings.revision,
    }
    
    new_access_token = create_access_token(
        identity=user.id,
        additional_claims={**additional_claims, "jti": str(uuid4())},
        expires_delta=access_expires,
    )
    
    new_refresh_token = create_refresh_token(
        identity=user.id,
        additional_claims={**additional_claims, "jti": new_refresh_jti, "family_id": family_id},
        expires_delta=refresh_expires,
    )
    
    # Store new refresh token
    new_token_obj = RefreshToken(
        jti=new_refresh_jti,
        user_id=user.id,
        family_id=family_id,
        expires_at=now + refresh_expires,
        revoked_at=None,
        replaced_by=None,
        created_at=now,
    )
    session.add(new_token_obj)
    session.commit()
    
    return new_access_token, new_refresh_token


def revoke_user_sessions(user_id: str, session: Session) -> int:
    """Revoke all refresh tokens for a user (logout all sessions).
    
    Args:
        user_id: User ID
        session: SQLAlchemy session
        
    Returns:
        Number of tokens revoked
    """
    now = datetime.now(timezone.utc)
    tokens = session.query(RefreshToken).filter_by(
        user_id=user_id,
        revoked_at=None,
    ).all()
    
    count = 0
    for token in tokens:
        token.revoked_at = now
        count += 1
    
    if count > 0:
        session.commit()
    
    return count


def is_refresh_token_valid(jti: str, session: Session) -> bool:
    """Check if a refresh token JTI is valid (exists, not revoked, not expired).
    
    Args:
        jti: Token JTI
        session: SQLAlchemy session
        
    Returns:
        True if valid, False otherwise
    """
    token = session.query(RefreshToken).filter_by(jti=jti).first()
    if not token:
        return False
    
    if token.revoked_at:
        return False
    
    if token.replaced_by:
        return False
    
    now = datetime.now(timezone.utc)
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    return expires_at >= now
