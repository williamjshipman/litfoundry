"""Add background jobs schema.

Revision ID: 006_jobs_schema
Revises: 005_project_acl_schema
Create Date: 2026-11-08 02:30:00.000000

This migration creates the jobs queue and coordination tables:
- jobs: Queue of background jobs with lease tracking for heartbeats
- active_writers: Registry of currently active write operations
- job_locked_works: Helper table for conflict checking when large numbers of work IDs are involved

Constraints:
- jobs has a unique index on idempotency_key scoped by requester
- jobs has a unique constraint on correlati on_id to support idempotency
- active_writers tracks who is writing what and when
- job_locked_works maps job_id to work_id for efficient RECORD_LOCKED checking
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_jobs_schema"
down_revision = "005_project_acl_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create background jobs and coordination tables."""
    
    # Create jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("requester_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),  # queued, running, partial, completed, failed, cancelling, cancelled
        sa.Column("idempotency_key", sa.String(256), nullable=True),  # scoped requester:key
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("not_before", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("lease_owner", sa.String(36), nullable=True),  # worker host/process ID
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("progress_json", sa.Text(), nullable=True),  # JSON progress state
        sa.Column("result_json", sa.Text(), nullable=True),  # JSON result or error
        sa.Column("scope_json", sa.Text(), nullable=True),  # JSON {"scope": "...", "work_ids": [...]}
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["project_directory.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("correlation_id", name="uq_jobs_correlation_id"),
    )
    
    # Index for job queries
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_requester_id", "jobs", ["requester_id"])
    op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_lease_owner", "jobs", ["lease_owner"])
    op.create_index("ix_jobs_not_before", "jobs", ["not_before"])
    
    # Unique index for idempotency key (including requester scoping)
    op.create_index(
        "ix_jobs_idempotency_key",
        "jobs",
        ["requester_id", "idempotency_key"],
        unique=True,
        sqlite_where="idempotency_key IS NOT NULL"
    )
    
    # Create active_writers table for write coordination
    op.create_table(
        "active_writers",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("operation", sa.String(64), nullable=False),  # operation type (e.g., "append", "merge")
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),  # "append", "records", "project"
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["project_directory.id"], ondelete="CASCADE"),
    )
    
    op.create_index("ix_active_writers_job_id", "active_writers", ["job_id"])
    op.create_index("ix_active_writers_project_id", "active_writers", ["project_id"])
    op.create_index("ix_active_writers_scope", "active_writers", ["scope"])
    op.create_index("ix_active_writers_expires_at", "active_writers", ["expires_at"])
    
    # Create job_locked_works table for efficient RECORD_LOCKED checking
    op.create_table(
        "job_locked_works",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("work_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )
    
    # Index for efficient work_id lookups
    op.create_index("ix_job_locked_works_work_id", "job_locked_works", ["work_id"])
    op.create_index("ix_job_locked_works_job_id", "job_locked_works", ["job_id"])
    op.create_index(
        "ix_job_locked_works_job_work",
        "job_locked_works",
        ["job_id", "work_id"],
        unique=True
    )


def downgrade() -> None:
    """Drop background jobs and coordination tables."""
    op.drop_index("ix_job_locked_works_job_work", table_name="job_locked_works")
    op.drop_index("ix_job_locked_works_job_id", table_name="job_locked_works")
    op.drop_index("ix_job_locked_works_work_id", table_name="job_locked_works")
    op.drop_table("job_locked_works")
    
    op.drop_index("ix_active_writers_expires_at", table_name="active_writers")
    op.drop_index("ix_active_writers_scope", table_name="active_writers")
    op.drop_index("ix_active_writers_project_id", table_name="active_writers")
    op.drop_index("ix_active_writers_job_id", table_name="active_writers")
    op.drop_table("active_writers")
    
    op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_not_before", table_name="jobs")
    op.drop_index("ix_jobs_lease_owner", table_name="jobs")
    op.drop_index("ix_jobs_type", table_name="jobs")
    op.drop_index("ix_jobs_project_id", table_name="jobs")
    op.drop_index("ix_jobs_requester_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
