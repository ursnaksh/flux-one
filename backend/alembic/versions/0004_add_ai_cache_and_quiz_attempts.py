"""Add Gemini AI cache and quiz attempt storage.

Revision ID: 0004_add_ai_storage
Revises: 0003_add_user_batch
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_add_ai_storage"
down_revision = "0003_add_user_batch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_cache",
        sa.Column("cache_key", sa.String(length=300), primary_key=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column(
            "subject_id",
            sa.BigInteger(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "topic_id",
            sa.BigInteger(),
            sa.ForeignKey("topics.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_cache_expires_at", "ai_cache", ["expires_at"])
    op.create_index("ix_ai_cache_subject_id", "ai_cache", ["subject_id"])

    op.create_table(
        "ai_quiz_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.BigInteger(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cache_key",
            sa.String(length=300),
            sa.ForeignKey("ai_cache.cache_key", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("total", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ai_quiz_attempts_user_created",
        "ai_quiz_attempts",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_quiz_attempts_user_created", table_name="ai_quiz_attempts")
    op.drop_table("ai_quiz_attempts")
    op.drop_index("ix_ai_cache_subject_id", table_name="ai_cache")
    op.drop_index("ix_ai_cache_expires_at", table_name="ai_cache")
    op.drop_table("ai_cache")
