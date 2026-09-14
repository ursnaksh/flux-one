from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import SessionStatus
from app.models.institution import TimetableSlot
from app.models.session import StudySession
from app.models.student import User


class DashboardRepository:
    """
    Persistence queries for dashboard aggregations and system operational telemetry.
    Strictly encapsulates database queries with zero business logic.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_division_timetable_for_day(
        self,
        division_id: int,
        day_of_week: int,
    ) -> List[TimetableSlot]:
        stmt = (
            select(TimetableSlot)
            .options(selectinload(TimetableSlot.subject))
            .where(
                TimetableSlot.division_id == division_id,
                TimetableSlot.day_of_week == day_of_week,
            )
            .order_by(TimetableSlot.start_time.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_system_metrics(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        # 1. Total users
        stmt_users = select(func.count(User.id)).where(User.is_active.is_(True))
        total_users = int((await self.db.execute(stmt_users)).scalar_one())

        # 2. Active sessions right now
        stmt_active = select(func.count(StudySession.id)).where(
            StudySession.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED])
        )
        active_now = int((await self.db.execute(stmt_active)).scalar_one())

        # 3. Sessions completed today
        stmt_completed = select(func.count(StudySession.id)).where(
            StudySession.status == SessionStatus.COMPLETED,
            StudySession.start_time >= start_of_today,
        )
        completed_today = int((await self.db.execute(stmt_completed)).scalar_one())

        # 4. Study minutes today
        stmt_minutes = select(func.coalesce(func.sum(StudySession.accumulated_active_seconds), 0)).where(
            StudySession.status == SessionStatus.COMPLETED,
            StudySession.start_time >= start_of_today,
        )
        seconds_today = int((await self.db.execute(stmt_minutes)).scalar_one())
        minutes_today = seconds_today // 60

        # 5. Global average focus
        stmt_focus = select(func.coalesce(func.avg(StudySession.focus_rating), 0.0)).where(
            StudySession.status == SessionStatus.COMPLETED,
            StudySession.focus_rating.is_not(None),
        )
        avg_focus = float((await self.db.execute(stmt_focus)).scalar_one())

        return {
            "total_registered_users": total_users,
            "active_sessions_now": active_now,
            "sessions_completed_today": completed_today,
            "study_minutes_today": minutes_today,
            "global_average_focus": round(avg_focus, 2),
        }
