"""Add barrier schema to system_leases.

Revision ID: 007_add_barrier_schema
Revises: 006_background_jobs_schema
Create Date: 2026-11-08 03:00:00.000000

This migration adds columns to system_leases to support the global write barrier:
- Barrier state (draining, frozen, released)
- Owner of the barrier (maintenance operation)
- Fencing token for exclusive barrier ownership
- Expiry time for barrier recovery
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007_add_barrier_schema"
down_revision = "006_background_jobs_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add barrier columns to system_leases table."""
    # Add name column to support named leases like "write-barrier"
    op.add_column(
        "system_leases",
        sa.Column("name", sa.String(64), nullable=True),  # Named lease (e.g., "write-barrier", "project-write:<uuid>")
    )
    
    # Add columns to system_leases for write barrier state
    op.add_column(
        "system_leases",
        sa.Column("state", sa.String(16), nullable=True),  # draining, frozen, released
    )
    op.add_column(
        "system_leases",
        sa.Column("owner", sa.String(36), nullable=True),  # Process ID holding the barrier
    )
    op.add_column(
        "system_leases",
        sa.Column("fencing_token", sa.Integer(), nullable=True),  # Monotonic token for exclusive ownership
    )
    
    # Add index for name-based lookups
    op.create_index(
        "ix_system_leases_name",
        "system_leases",
        ["name"],
        unique=True,
    )
    
    # Note: expires_at already exists on system_leases from earlier migrations


def downgrade() -> None:
    """Remove barrier columns from system_leases table."""
    op.drop_index(
        "ix_system_leases_name",
        table_name="system_leases"
    )
    op.drop_column("system_leases", "fencing_token")
    op.drop_column("system_leases", "owner")
    op.drop_column("system_leases", "state")
    op.drop_column("system_leases", "name")
