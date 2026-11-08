"""Initial project database schema.

Revision ID: 001_initial
Revises:
Create Date: 2026-11-08 02:10:00.000000

This migration creates the initial schema for a project database:
- project_info: Project metadata (title, description, objectives, research questions)
- project_audit_events: Audit trail of changes within the project
- project_people: Team members and contributors

Constraints:
- project_info.id is unique (single row per project)
- project_audit_events.project_info_id foreign keys to project_info
- project_people.project_info_id foreign keys to project_info
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial project database schema."""
    
    # Create project_info table (single row, project metadata)
    op.create_table(
        "project_info",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objectives", sa.Text(), nullable=True),
        sa.Column("research_questions", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    
    # Create project_audit_events table
    op.create_table(
        "project_audit_events",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("project_info_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("actor_user_id", sa.String(36), nullable=True),  # May be external in imports
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), default="success", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_info_id"], ["project_info.id"], ondelete="CASCADE"),
    )
    
    # Index for efficient project audit lookups
    op.create_index(
        "ix_project_audit_events_project_info_id",
        "project_audit_events",
        ["project_info_id"]
    )
    
    # Index for efficient resource lookups
    op.create_index(
        "ix_project_audit_events_resource",
        "project_audit_events",
        ["resource_type", "resource_id"]
    )
    
    # Create project_people table (team members and contributors)
    op.create_table(
        "project_people",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("project_info_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),  # May be null for external contributors
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("affiliation", sa.String(512), nullable=True),
        sa.Column("role", sa.String(64), nullable=True),  # e.g., 'reviewer', 'author', 'contributor'
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_info_id"], ["project_info.id"], ondelete="CASCADE"),
    )
    
    # Index for efficient people lookups
    op.create_index(
        "ix_project_people_project_info_id",
        "project_people",
        ["project_info_id"]
    )


def downgrade() -> None:
    """Drop initial project database schema."""
    op.drop_index(
        "ix_project_people_project_info_id",
        table_name="project_people"
    )
    op.drop_table("project_people")
    op.drop_index(
        "ix_project_audit_events_resource",
        table_name="project_audit_events"
    )
    op.drop_index(
        "ix_project_audit_events_project_info_id",
        table_name="project_audit_events"
    )
    op.drop_table("project_audit_events")
    op.drop_table("project_info")
