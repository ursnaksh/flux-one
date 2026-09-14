import uuid
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import SessionStatus
from app.models.session import StudySession
from app.models.student import AcademicBrain, Streak


class SessionRepository:
    """
    Persistence boundary for Study Sessions and related student statistical entities.
    Strictly encapsulates database queries with zero domain business logic.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_or_paused_session(self, user_id: uuid.UUID) -> Optional[StudySession]:
        stmt = (
            select(StudySession)
            .options(
                selectinload(StudySession.subject),
                selectinload(StudySession.topic),
            )
            .where(
                StudySession.user_id == user_id,
                StudySession.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED]),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, session_id: uuid.UUID) -> Optional[StudySession]:
        stmt = (
            select(StudySession)
            .options(
                selectinload(StudySession.subject),
                selectinload(StudySession.topic),
            )
            .where(StudySession.id == session_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_session(self, session: StudySession) -> StudySession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_user_streak(self, user_id: uuid.UUID) -> Optional[Streak]:
        stmt = select(Streak).where(Streak.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_academic_brain(self, user_id: uuid.UUID) -> Optional[AcademicBrain]:
        stmt = select(AcademicBrain).where(AcademicBrain.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_study_minutes_for_date(self, user_id: uuid.UUID, target_date: date) -> int:
        start_of_day = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        stmt = (
            select(func.coalesce(func.sum(StudySession.accumulated_active_seconds), 0))
            .where(
                StudySession.user_id == user_id,
                StudySession.status == SessionStatus.COMPLETED,
                StudySession.start_time >= start_of_day,
            )
        )
        result = await self.db.execute(stmt)
        seconds = int(result.scalar_one())
        return seconds // 60

    async def get_longest_session_minutes(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.coalesce(func.max(StudySession.accumulated_active_seconds), 0))
            .where(
                StudySession.user_id == user_id,
                StudySession.status == SessionStatus.COMPLETED,
            )
        )
        result = await self.db.execute(stmt)
        seconds = int(result.scalar_one())
        return seconds // 60

    async def get_completed_sessions_count(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(StudySession.id))
            .where(
                StudySession.user_id == user_id,
                StudySession.status == SessionStatus.COMPLETED,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def list_user_sessions(self, user_id: uuid.UUID, limit: int = 10) -> List[StudySession]:
        stmt = (
            select(StudySession)
            .options(
                selectinload(StudySession.subject),
                selectinload(StudySession.topic),
            )
            .where(StudySession.user_id == user_id)
            .order_by(StudySession.start_time.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
