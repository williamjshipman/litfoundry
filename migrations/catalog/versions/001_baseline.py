"""Initial catalogue baseline.

Revision ID: 001_baseline
Revises:
Create Date: 2026-10-23 23:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial catalogue schema."""
    # Create schema_meta table to track migration metadata
    op.create_table(
        "schema_meta",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema_name", sa.String(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("schema_name"),
    )

    # Create system_settings table
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # Initialize schema version
    op.execute(
        "INSERT INTO schema_meta (version, schema_name, last_updated) "
        "VALUES (1, 'litfoundry', CURRENT_TIMESTAMP)"
    )


def downgrade() -> None:
    """Drop initial catalogue schema."""
    op.drop_table("system_settings")
    op.drop_table("schema_meta")
