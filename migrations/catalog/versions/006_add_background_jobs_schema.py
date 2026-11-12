"""Add background jobs schema.

Revision ID: 006_background_jobs_schema
Revises: 005_project_acl_schema
Create Date: 2026-11-08 02:26:00.000000

This migration creates the background job queue and write coordination tables:
- jobs: The job queue with status, lease, and retry tracking
- active_writers: Registry of currently running write operations
- job_locked_works: Index of work IDs locked by records jobs (for efficient conflict detection)

Constraints:
- jobs.id is unique (job UUID)
- jobs.idempotency_key is unique within a requester (user_id)
- active_writers tracks running write operations with lease expiry
- job_locked_works indexes work IDs for efficient RECORD_LOCKED conflict detection
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_background_jobs_schema"
down_revision = "005_project_acl_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create background jobs and write coordination tables."""
    
    # Create jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),  # NULL for system jobs
        sa.Column("user_id", sa.String(36), nullable=False),  # requester
        sa.Column("type", sa.String(64), nullable=False),  # import, merge, etc.
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),  # queued, running, partial, completed, failed, cancelling, cancelled
        sa.Column("scope_json", sa.Text(), nullable=True),  # {"scope": "append|records|project", "work_ids": [...]}
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),  # 0-100, higher runs first
        sa.Column("not_before", sa.DateTime(), nullable=False),  # Delay queue entry until this time
        sa.Column("lease_owner", sa.String(36), nullable=True),  # Worker ID holding the lease
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),  # Lease expiry time
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),  # Current attempt number
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),  # Max retries
        sa.Column("progress_json", sa.Text(), nullable=True),  # Structured progress data
        sa.Column("error_code", sa.String(64), nullable=True),  # JOB_FAILED, FORBIDDEN, etc.
        sa.Column("error_message", sa.Text(), nullable=True),  # Redacted error message
        sa.Column("error_cause", sa.String(64), nullable=True),  # Typed cause like SOURCE_ACCESS_DENIED
        sa.Column("correlation_id", sa.String(36), nullable=True),  # Trace correlation ID
        sa.Column("idempotency_key", sa.String(256), nullable=True),  # Client-supplied key for idempotency
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),  # When the job started running
        sa.Column("completed_at", sa.DateTime(), nullable=True),  # When the job finished
        sa.ForeignKeyConstraint(["project_id"], ["project_directory.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_jobs_user_idempotency"),
    )
    
    # Index for queue claiming (status, not_before, priority, created_at)
    op.create_index(
        "ix_jobs_queue",
        "jobs",
        ["status", "not_before", "priority", "created_at"],
    )
    
    # Index for user's jobs
    op.create_index(
        "ix_jobs_user_id",
        "jobs",
        ["user_id"],
    )
    
    # Index for project's jobs
    op.create_index(
        "ix_jobs_project_id",
        "jobs",
        ["project_id"],
    )
    
    # Index for lease recovery (expired leases)
    op.create_index(
        "ix_jobs_lease_expires_at",
        "jobs",
        ["lease_expires_at"],
    )
    
    # Create active_writers table for barrier coordination
    op.create_table(
        "active_writers",
        sa.Column("id", sa.String(36), nullable=False, primary_key=True),
        sa.Column("job_id", sa.String(36), nullable=True),  # NULL for web requests
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),  # append, records, project
        sa.Column("lease_expires_at", sa.DateTime(), nullable=False),
        sa.Column("registered_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["project_directory.id"], ondelete="CASCADE"),
    )
    
    # Index for barrier check (by project and expiry)
    op.create_index(
        "ix_active_writers_project_expires",
        "active_writers",
        ["project_id", "lease_expires_at"],
    )
    
    # Index for lease recovery
    op.create_index(
        "ix_active_writers_lease_expires",
        "active_writers",
        ["lease_expires_at"],
    )
    
    # Create job_locked_works table for efficient RECORD_LOCKED conflict detection
    op.create_table(
        "job_locked_works",
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("work_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id", "work_id"),
    )
    
    # Index for efficient conflict detection (by work_id)
    op.create_index(
        "ix_job_locked_works_work_id",
        "job_locked_works",
        ["work_id"],
    )


def downgrade() -> None:
    """Drop background jobs and write coordination tables."""
    op.drop_index(
        "ix_job_locked_works_work_id",
        table_name="job_locked_works"
    )
    op.drop_table("job_locked_works")
    
    op.drop_index(
        "ix_active_writers_lease_expires",
        table_name="active_writers"
    )
    op.drop_index(
        "ix_active_writers_project_expires",
        table_name="active_writers"
    )
    op.drop_table("active_writers")
    
    op.drop_index(
        "ix_jobs_lease_expires_at",
        table_name="jobs"
    )
    op.drop_index(
        "ix_jobs_project_id",
        table_name="jobs"
    )
    op.drop_index(
        "ix_jobs_user_id",
        table_name="jobs"
    )
    op.drop_index(
        "ix_jobs_queue",
        table_name="jobs"
    )
    op.drop_table("jobs")
