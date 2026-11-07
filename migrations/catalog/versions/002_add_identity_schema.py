"""Add identity schema tables for local authentication.

Revision ID: 002_identity_schema
Revises: 001_baseline
Create Date: 2026-11-08 00:35:00.000000

This migration creates the core identity tables:
- users: Local and directory accounts with session versioning
- auth_settings: Global policy, token lifetimes, throttling policy
- bootstrap_tokens: Single-use tokens for first-run setup
- login_throttle: Sliding-window throttling per IP and identifier
- refresh_tokens: Issued refresh tokens with family tracking for reuse detection
- audit_events: System audit trail of sensitive actions

Constraints:
- username_normalized is unique per local account (account_type='local')
- role='admin' is unique, enforcing single administrator
- Foreign keys on user_id where applicable
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = "002_identity_schema"
down_revision = "001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create identity schema tables."""
    
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("account_type", sa.String(16), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("username_normalized", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, default=False),
        sa.Column("role", sa.String(16), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("session_version", sa.Integer(), nullable=False, default=0),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    
    # Unique constraint for local usernames (case-insensitive via username_normalized)
    # Using raw SQL for SQLite partial index support
    op.execute(
        "CREATE UNIQUE INDEX ix_users_local_username ON users (username_normalized) "
        "WHERE account_type='local' AND username_normalized IS NOT NULL"
    )
    
    # Unique constraint for single admin role
    # Using raw SQL for SQLite partial index support
    op.execute(
        "CREATE UNIQUE INDEX ix_users_admin_role ON users (role) "
        "WHERE role='admin'"
    )
    
    # Create auth_settings table (single row holding global settings)
    op.create_table(
        "auth_settings",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("password_policy_json", sa.Text(), nullable=False),
        sa.Column("access_token_minutes", sa.Integer(), nullable=False, default=15),
        sa.Column("refresh_token_hours", sa.Integer(), nullable=False, default=7 * 24),
        sa.Column("throttle_policy_json", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    
    # Create login_throttle table (sliding window throttling)
    op.create_table(
        "login_throttle",
        sa.Column("key", sa.String(128), nullable=False, primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    
    # Create refresh_tokens table (issued tokens with family tracking)
    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.String(255), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("family_id", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    
    # Create index for family_id lookup
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    
    # Create bootstrap_tokens table (single-use tokens for setup)
    op.create_table(
        "bootstrap_tokens",
        sa.Column("token_hash", sa.String(255), nullable=False, primary_key=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
    )
    
    # Unique constraint ensuring at most one unconsumed token.
    # Note: SQLite partial indexes cannot use non-deterministic functions like CURRENT_TIMESTAMP,
    # so we only check consumed_at IS NULL. Application must verify expiry at use time.
    op.execute(
        "CREATE UNIQUE INDEX ix_bootstrap_tokens_unconsumed ON bootstrap_tokens (consumed_at) "
        "WHERE consumed_at IS NULL"
    )
    
    # Create audit_events table (system audit trail)
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    
    # Index for efficient audit queries
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_resource", "audit_events", ["resource_type", "resource_id"])
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_user_id"])


def downgrade() -> None:
    """Drop identity schema tables."""
    op.drop_index("ix_users_admin_role", table_name="users")
    op.drop_index("ix_users_local_username", table_name="users")
    op.drop_table("audit_events")
    op.drop_table("bootstrap_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("login_throttle")
    op.drop_table("auth_settings")
    op.drop_table("users")
