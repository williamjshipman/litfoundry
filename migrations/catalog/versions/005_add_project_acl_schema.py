"""Add project access control (ACL) schema.

Revision ID: 005_project_acl_schema
Revises: 004_project_directory_schema
Create Date: 2026-11-08 02:15:00.000000

This migration creates the project_acl table for per-project access control:
- project_acl: Maps users to roles (viewer, editor, deny) for specific projects
  with an explicit grant timestamp to track when the entry was created.

Constraints:
- project_acl has a unique constraint on (project_id, user_id) to prevent duplicates
- Roles are: viewer, editor, deny
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005_project_acl_schema"
down_revision = "004_project_directory_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create project access control (ACL) table."""
    
    # Create project_acl table
    op.create_table(
        "project_acl",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),  # viewer, editor, deny
        sa.Column("granted_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["project_directory.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_acl_project_user"),
    )
    
    # Index for efficient project lookups
    op.create_index(
        "ix_project_acl_project_id",
        "project_acl",
        ["project_id"]
    )
    
    # Index for efficient user lookups
    op.create_index(
        "ix_project_acl_user_id",
        "project_acl",
        ["user_id"]
    )


def downgrade() -> None:
    """Drop project access control (ACL) table."""
    op.drop_index(
        "ix_project_acl_user_id",
        table_name="project_acl"
    )
    op.drop_index(
        "ix_project_acl_project_id",
        table_name="project_acl"
    )
    op.drop_table("project_acl")
