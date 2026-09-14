import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, TimestampMixin
from app.models.enums import EnrollmentStatus, IdentityProvider


class User(Base, TimestampMixin, AuditMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("prn_number", name="uq_users_prn_number"),
        Index("ix_users_college_dept_div", "college_id", "department_id", "division_id"),
    )
    __mapper_args__ = {
        "version_id_col": "version_id",
    }

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_value=uuid.uuid4,
        default=uuid.uuid4,
        primary_key=True,
        index=True,
    )
    college_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("colleges.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    division_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("divisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    prn_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    identities: Mapped[List["UserIdentity"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    enrollments: Mapped[List["Enrollment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    streak: Mapped[Optional["Streak"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    academic_brain: Mapped[Optional["AcademicBrain"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class UserIdentity(Base, TimestampMixin, AuditMixin):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_identities_email"),
        UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_user"),
        Index("ix_user_identities_user_id", "user_id"),
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
    )
    provider: Mapped[IdentityProvider] = mapped_column(
        SQLEnum(IdentityProvider, name="identity_provider_enum"),
        nullable=False,
        default=IdentityProvider.LOCAL,
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Email for LOCAL, OAuth subject ID for GOOGLE",
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="identities")


class Enrollment(Base, TimestampMixin, AuditMixin):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_id", name="uq_enrollment_user_subject"),
        Index("ix_enrollments_user_id", "user_id"),
        Index("ix_enrollments_subject_id", "subject_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        SQLEnum(EnrollmentStatus, name="enrollment_status_enum"),
        nullable=False,
        default=EnrollmentStatus.ACTIVE,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="enrollments")


class Streak(Base, TimestampMixin, AuditMixin):
    __tablename__ = "streaks"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_streaks_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_study_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="streak")


class AcademicBrain(Base, TimestampMixin, AuditMixin):
    __tablename__ = "academic_brains"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_academic_brains_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_study_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_focus_rating: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    average_quiz_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_ai_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="academic_brain")
