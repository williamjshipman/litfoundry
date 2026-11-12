"""Catalogue database ORM models for identity and system state."""

from datetime import datetime
from typing import Optional
from uuid import UUID
import json

from sqlalchemy import ForeignKey, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all catalogue models."""
    pass


class User(Base):
    """User account model (local or directory)."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    username_normalized: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    session_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="actor_user", cascade="all, delete-orphan"
    )


class AuthSettings(Base):
    """Global authentication settings (single row)."""
    
    __tablename__ = "auth_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    password_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    refresh_token_hours: Mapped[int] = mapped_column(Integer, default=7 * 24, nullable=False)
    throttle_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class LoginThrottle(Base):
    """Sliding-window throttling state for login attempts."""
    
    __tablename__ = "login_throttle"
    
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class RefreshToken(Base):
    """Issued refresh token with family tracking for reuse detection."""
    
    __tablename__ = "refresh_tokens"
    
    jti: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    family_id: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replaced_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


class BootstrapToken(Base):
    """Single-use bootstrap token for first-run setup."""
    
    __tablename__ = "bootstrap_tokens"
    
    token_hash: Mapped[str] = mapped_column(String(255), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditEvent(Base):
    """System audit trail of sensitive actions."""
    
    __tablename__ = "audit_events"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationship
    actor_user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_events")


class DirectoryConfig(Base):
    """Active Directory configuration (single row when enabled)."""
    
    __tablename__ = "directory_config"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    domain_name: Mapped[str] = mapped_column(String(255), nullable=False)
    netbios_name: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    upn_suffixes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    domain_controllers_json: Mapped[str] = mapped_column(Text, nullable=False)
    base_dn: Mapped[str] = mapped_column(String(512), nullable=False)
    tls_mode: Mapped[str] = mapped_column(String(16), nullable=False)  # 'ldaps' or 'starttls'
    ca_bundle_pem_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connection_timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    read_timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    revalidation_interval_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    service_account_username: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    service_account_password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_test_passed_revision: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_directory_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    directory_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DirectoryIdentityBinding(Base):
    """Binding between a LitFoundry user and an Active Directory identity."""
    
    __tablename__ = "directory_identity_bindings"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    sid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    guid: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    samaccountname_normalized: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    upn_normalized: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationship
    user: Mapped["User"] = relationship("User")


class ProjectDirectory(Base):
    """Project metadata and lifecycle state in the catalogue."""
    
    __tablename__ = "project_directory"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    public_access: Mapped[str] = mapped_column(String(16), default="none", nullable=False)  # none, viewer, editor
    state_code: Mapped[str] = mapped_column(String(16), default="ready", nullable=False)  # provisioning, ready, archived, deleting, quarantined, error
    project_schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationship
    owner: Mapped["User"] = relationship("User")


class SystemLease(Base):
    """Fenced system-wide lease for maintenance and backup operations."""
    
    __tablename__ = "system_leases"
    
    lease_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    holder_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProjectACL(Base):
    """Per-project access control entry mapping users to roles."""
    
    __tablename__ = "project_acl"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_directory.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # viewer, editor, deny
    granted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

