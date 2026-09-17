import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, TimestampMixin
from app.models.enums import SessionSource, SessionStatus
from app.models.institution import Subject, Topic


class StudySession(Base, TimestampMixin, AuditMixin):
    __tablename__ = "study_sessions"
    __table_args__ = (
        Index(
            "uq_user_active_session",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('ACTIVE', 'PAUSED')"),
        ),
        Index("ix_study_sessions_user_start", "user_id", "start_time"),
        CheckConstraint(
            "focus_rating IS NULL OR (focus_rating >= 1 AND focus_rating <= 5)",
            name="ck_focus_rating_range",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        default=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, name="session_status_enum"),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )
    source: Mapped[SessionSource] = mapped_column(
        SQLEnum(SessionSource, name="session_source_enum"),
        nullable=False,
        default=SessionSource.MOBILE,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accumulated_active_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    target_duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        default=45,
        nullable=True,
    )
    focus_rating: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    reflection_note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    version_id: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    # Relationships
    subject: Mapped["Subject"] = relationship(lazy="selectin")
    topic: Mapped[Optional["Topic"]] = relationship(lazy="selectin")
