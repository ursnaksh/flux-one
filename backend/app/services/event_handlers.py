from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import DomainEvent
from app.repositories.session_repository import SessionRepository


@dataclass
class StudySessionCompletedEvent(DomainEvent):
    user_id: int
    session_id: int
    subject_id: int
    topic_id: Optional[int]
    duration_minutes: int
    focus_rating: int
    completed_at: datetime


class EventProcessor:
    """
    Processes domain events and updates secondary projections
    (streaks, academic brain metrics, topic mastery).
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SessionRepository(db)

    async def handle_session_completed(self, event: StudySessionCompletedEvent) -> None:
        # 1. Update Streak
        streak = await self.repo.get_or_create_streak(event.user_id)
        now_date = event.completed_at.date()

        if streak.last_study_date:
            last_date = streak.last_study_date.date()
            if now_date == last_date + timedelta(days=1):
                streak.current_streak += 1
            elif now_date > last_date + timedelta(days=1):
                streak.current_streak = 1
        else:
            streak.current_streak = 1

        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        streak.last_study_date = event.completed_at

        # 2. Update Academic Brain & Topic Mastery
        brain = await self.repo.get_academic_brain(event.user_id)
        if brain:
            brain.total_study_minutes += event.duration_minutes

            # Smooth Focus Rating Running Average
            if brain.average_focus_rating == 0.0:
                brain.average_focus_rating = float(event.focus_rating)
            else:
                brain.average_focus_rating = round(
                    (brain.average_focus_rating * 0.8) + (event.focus_rating * 0.2), 2
                )

            # Update Topic Mastery if topic was tagged
            if event.topic_id:
                topic_key = str(event.topic_id)
                mastery_map = dict(brain.topic_mastery or {})
                topic_data = mastery_map.get(topic_key, {
                    "topic_id": event.topic_id,
                    "mastery": 0.5,
                    "confidence": 0.5,
                    "study_minutes": 0,
                    "last_revision": None,
                })

                topic_data["study_minutes"] += event.duration_minutes
                topic_data["last_revision"] = event.completed_at.isoformat()

                # Focus rating of 4-5 boosts confidence slightly; 1-2 decreases it
                confidence_delta = (event.focus_rating - 3) * 0.05
                topic_data["confidence"] = max(0.1, min(1.0, round(topic_data["confidence"] + confidence_delta, 2)))

                mastery_map[topic_key] = topic_data
                brain.topic_mastery = mastery_map

            brain.last_ai_update = datetime.now(timezone.utc)

        await self.db.flush()
