"""Add timetable batch support.

Revision ID: 0002_add_timetable_batch
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_timetable_batch"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "timetable_slots",
        sa.Column(
            "batch",
            sa.String(length=20),
            nullable=False,
            server_default="ALL",
        ),
    )

    op.drop_constraint(
        "uq_timetable_slot_division_day_time",
        "timetable_slots",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_timetable_slot_schedule",
        "timetable_slots",
        [
            "division_id",
            "day_of_week",
            "start_time",
            "subject_id",
            "batch",
        ],
    )

    op.alter_column(
        "timetable_slots",
        "batch",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_timetable_slot_schedule",
        "timetable_slots",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_timetable_slot_division_day_time",
        "timetable_slots",
        ["division_id", "day_of_week", "start_time"],
    )

    op.drop_column("timetable_slots", "batch")