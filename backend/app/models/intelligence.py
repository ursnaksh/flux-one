from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class AcademicBrain(Base, TimestampMixin):
    __tablename__ = "academic_brains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Core performance metrics
    consistency_score: Mapped[float] = mapped_column(Float, default=100.0)
    average_focus_rating: Mapped[float] = mapped_column(Float, default=0.0)
    average_quiz_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_study_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # Quantitative Dynamic Mastery Map: { "topic_id": { "mastery": 0.75, "confidence": 0.8, "study_minutes": 120, "last_revision": "..." } }
    topic_mastery: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    revision_queue: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)

    last_ai_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="academic_brain")


class AIGeneration(Base, TimestampMixin):
    __tablename__ = "ai_generations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    generation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)


class QuizAttempt(Base, TimestampMixin):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generation_id: Mapped[int] = mapped_column(ForeignKey("ai_generations.id", ondelete="CASCADE"), nullable=False)
    answers: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)
