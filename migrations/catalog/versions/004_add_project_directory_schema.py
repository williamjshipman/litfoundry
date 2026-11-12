"""Add project directory schema.

Revision ID: 004_project_directory_schema
Revises: 003_directory_schema
Create Date: 2026-11-08 02:00:00.000000

This migration creates the project directory table that tracks all projects:
- project_directory: Metadata and lifecycle state for each project
- system_leases: Fenced system-wide leases for maintenance and backup operations

Constraints:
- project_directory.id is unique (project UUID)
- project_directory.state_code tracks the lifecycle (provisioning, ready, archived, etc.)
- system_leases.lease_key is unique (one lease per operation type)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "004_project_directory_schema"
down_revision = "003_directory_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project directory and system leases tables."""
    
    # Create project_directory table
    op.create_table(
        "project_directory",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("relative_path", sa.String(512), nullable=False, unique=True),
        sa.Column("owner_user_id", sa.String(36), nullable=False),
        sa.Column("public_access", sa.String(16), nullable=False, server_default="none"),  # none, viewer, editor
        sa.Column("state_code", sa.String(16), nullable=False, server_default="ready"),  # provisioning, ready, archived, deleting, quarantined, error
        sa.Column("project_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    
    # Index for owner lookups
    op.create_index(
        "ix_project_directory_owner_user_id",
        "project_directory",
        ["owner_user_id"]
    )
    
    # Index for state lookups
    op.create_index(
        "ix_project_directory_state_code",
        "project_directory",
        ["state_code"]
    )
    
    # Create system_leases table for fenced operations
    op.create_table(
        "system_leases",
        sa.Column("lease_key", sa.String(64), nullable=False, primary_key=True),
        sa.Column("holder_id", sa.String(36), nullable=True),  # UUID or process ID
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
    )
    
    # Index for expiration cleanup
    op.create_index(
        "ix_system_leases_expires_at",
        "system_leases",
        ["expires_at"]
    )


def downgrade() -> None:
    """Drop project directory and system leases tables."""
    op.drop_index(
        "ix_system_leases_expires_at",
        table_name="system_leases"
    )
    op.drop_table("system_leases")
    op.drop_index(
        "ix_project_directory_state_code",
        table_name="project_directory"
    )
    op.drop_index(
        "ix_project_directory_owner_user_id",
        table_name="project_directory"
    )
    op.drop_table("project_directory")
