"""Add student batch.

Revision ID: 0003_add_user_batch
Revises: 0002_add_timetable_batch
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_user_batch"
down_revision = "0002_add_timetable_batch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("batch", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "batch")
    