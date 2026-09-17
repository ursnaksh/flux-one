"""Persist student notes and assignment state.

Revision ID: 0005_add_student_content
Revises: 0004_add_ai_storage
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_student_content"
down_revision = "0004_add_ai_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(length=80), nullable=False),
        sa.Column("subject_id", sa.BigInteger(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(length=300), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "client_id", name="uq_student_notes_user_client"),
    )
    op.create_index("ix_student_notes_user_updated", "student_notes", ["user_id", "updated_at"])

    op.create_table(
        "student_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(length=80), nullable=False),
        sa.Column("subject_id", sa.BigInteger(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(length=300), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("due_text", sa.String(length=120), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="med"),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "client_id", name="uq_student_assignments_user_client"),
    )
    op.create_index(
        "ix_student_assignments_user_done",
        "student_assignments",
        ["user_id", "is_done", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_assignments_user_done", table_name="student_assignments")
    op.drop_table("student_assignments")
    op.drop_index("ix_student_notes_user_updated", table_name="student_notes")
    op.drop_table("student_notes")
