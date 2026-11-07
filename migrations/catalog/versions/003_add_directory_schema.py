"""Add Active Directory configuration and identity bindings schema.

Revision ID: 003_directory_schema
Revises: 002_identity_schema
Create Date: 2026-11-08 01:00:00.000000

This migration creates the Active Directory integration tables:
- directory_config: Single-row configuration for one AD domain
- directory_identity_bindings: Maps LitFoundry users to their AD identities via SID

Constraints:
- directory_config.id is always 1 (single domain configuration)
- directory_identity_bindings.user_id is unique (one user → one AD identity)
- directory_identity_bindings.sid is unique (one SID → one user)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003_directory_schema"
down_revision = "002_identity_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create Active Directory schema tables."""
    
    # Create directory_config table (single row configuration)
    op.create_table(
        "directory_config",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("domain_name", sa.String(255), nullable=False),
        sa.Column("netbios_name", sa.String(15), nullable=True),
        sa.Column("upn_suffixes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("domain_controllers_json", sa.Text(), nullable=False),
        sa.Column("base_dn", sa.String(512), nullable=False),
        sa.Column("tls_mode", sa.String(16), nullable=False),  # 'ldaps' or 'starttls'
        sa.Column("ca_bundle_pem_encrypted", sa.Text(), nullable=True),
        sa.Column("connection_timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("read_timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("revalidation_interval_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("service_account_username", sa.String(512), nullable=True),
        sa.Column("service_account_password_encrypted", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_test_passed_revision", sa.Integer(), nullable=True),
        sa.Column("last_directory_success_at", sa.DateTime(), nullable=True),
        sa.Column("directory_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    
    # Create directory_identity_bindings table with unique constraints inline
    op.create_table(
        "directory_identity_bindings",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, unique=True),
        sa.Column("sid", sa.String(255), nullable=False, unique=True),
        sa.Column("guid", sa.String(36), nullable=True),
        sa.Column("samaccountname_normalized", sa.String(255), nullable=True),
        sa.Column("upn_normalized", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    
    # Index for efficient user_id lookup
    op.create_index(
        "ix_directory_identity_bindings_user_id",
        "directory_identity_bindings",
        ["user_id"]
    )
    
    # Index for efficient SID lookup
    op.create_index(
        "ix_directory_identity_bindings_sid",
        "directory_identity_bindings",
        ["sid"]
    )


def downgrade() -> None:
    """Drop Active Directory schema tables."""
    op.drop_index(
        "ix_directory_identity_bindings_sid",
        table_name="directory_identity_bindings"
    )
    op.drop_index(
        "ix_directory_identity_bindings_user_id",
        table_name="directory_identity_bindings"
    )
    op.drop_table("directory_identity_bindings")
    op.drop_table("directory_config")
