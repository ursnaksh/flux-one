from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import SubjectType


class College(Base, TimestampMixin):
    __tablename__ = "colleges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    time_zone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")
    erp_portal_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    departments: Mapped[List["Department"]] = relationship(
        back_populates="college",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("college_id", "code", name="uq_department_college_code"),
        Index("ix_departments_college_id", "college_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    college_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)

    college: Mapped["College"] = relationship(back_populates="departments")
    semesters: Mapped[List["Semester"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Semester(Base, TimestampMixin):
    __tablename__ = "semesters"
    __table_args__ = (
        UniqueConstraint("department_id", "semester_number", "academic_year", name="uq_semester_dept_num_year"),
        Index("ix_semesters_department_id", "department_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    semester_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)

    department: Mapped["Department"] = relationship(back_populates="semesters")
    divisions: Mapped[List["Division"]] = relationship(
        back_populates="semester",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subjects: Mapped[List["Subject"]] = relationship(
        back_populates="semester",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Division(Base, TimestampMixin):
    __tablename__ = "divisions"
    __table_args__ = (
        UniqueConstraint("semester_id", "name", name="uq_division_semester_name"),
        Index("ix_divisions_semester_id", "semester_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    semester_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    semester: Mapped["Semester"] = relationship(back_populates="divisions")
    timetable_slots: Mapped[List["TimetableSlot"]] = relationship(
        back_populates="division",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("semester_id", "code", name="uq_subject_semester_code"),
        Index("ix_subjects_semester_id", "semester_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    semester_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    credits: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    subject_type: Mapped[SubjectType] = mapped_column(
        SQLEnum(SubjectType, name="subject_type_enum"),
        nullable=False,
        default=SubjectType.THEORY,
    )

    semester: Mapped["Semester"] = relationship(back_populates="subjects")
    topics: Mapped[List["Topic"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("subject_id", "unit_number", "title", name="uq_topic_subject_unit_title"),
        Index("ix_topics_subject_id", "subject_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    unit_number: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    subject: Mapped["Subject"] = relationship(back_populates="topics")


class TimetableSlot(Base, TimestampMixin):
    __tablename__ = "timetable_slots"
    __table_args__ = UniqueConstraint(
    "division_id",
    "day_of_week",
    "start_time",
    "subject_id",
    "batch",
    name="uq_timetable_slot_schedule",
),

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    semester_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("semesters.id", ondelete="CASCADE"),
        nullable=False,
    )
    division_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("divisions.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="1=Monday, 7=Sunday",
    )
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    instructor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    batch: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="ALL",
)

    semester: Mapped["Semester"] = relationship()
    division: Mapped["Division"] = relationship(back_populates="timetable_slots")
    subject: Mapped["Subject"] = relationship()
