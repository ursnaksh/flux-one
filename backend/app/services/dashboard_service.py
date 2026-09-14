import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import College, Department, Division
from app.models.student import User
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.institution_repository import InstitutionRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import SubjectSimpleResponse
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    SystemMetricsResponse,
    TodayScheduleSlot,
)
from app.schemas.session import SessionResponse
from app.services.recommendation_service import RecommendationService


class DashboardService:
    """
    Pure aggregation orchestrator for student dashboard and system operational metrics.
    Aggregates pre-computed projections from repositories without executing inline business calculations.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)
        self.institution_repo = InstitutionRepository(db)
        self.dashboard_repo = DashboardRepository(db)

    async def get_student_dashboard(self, user_id: uuid.UUID) -> DashboardOverviewResponse:
        # 1. Fetch User and pre-computed projections
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")

        # 2. Institutional Metadata
        college = await self.db.get(College, user.college_id)
        dept = await self.db.get(Department, user.department_id)
        division = await self.db.get(Division, user.division_id) if user.division_id else None

        # 3. Aggregated Operational Metrics from Repositories
        now = datetime.now(timezone.utc)
        today = now.date()

        study_minutes_today = await self.session_repo.get_study_minutes_for_date(user_id, today)
        active_session = await self.session_repo.get_active_or_paused_session(user_id)
        enrolled_subjects_db = await self.user_repo.get_enrolled_subjects_for_user(user_id)
        enrolled_subjects = [SubjectSimpleResponse.from_orm(s) for s in enrolled_subjects_db]

        # 4. Today's Class Schedule (day_of_week: Monday=1, Sunday=7)
        day_of_week = now.isoweekday()
        schedule_slots: List[TodayScheduleSlot] = []
        if user.division_id:
            slots = await self.dashboard_repo.get_division_timetable_for_day(user.division_id, day_of_week)
            schedule_slots = [
                TodayScheduleSlot(
                    subject_name=slot.subject.name,
                    subject_code=slot.subject.code,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    location=slot.location,
                    instructor_name=slot.instructor_name,
                )
                for slot in slots
            ]

        # 5. Discipline & Cognitive Projections
        streak = user.streak
        brain = user.academic_brain
        current_streak = streak.current_streak if streak else 0
        longest_streak = streak.longest_streak if streak else 0
        consistency_score = brain.consistency_score if brain else 100.0

        # 6. Actionable Recommendation via dedicated RecommendationService
        rec = RecommendationService.get_daily_nudge(
            active_session=active_session,
            current_streak=current_streak,
            study_minutes_today=study_minutes_today,
            enrolled_subjects=enrolled_subjects,
        )

        # 7. Map active session if present
        active_session_res: Optional[SessionResponse] = None
        if active_session:
            active_session_res = SessionResponse(
                id=active_session.id,
                user_id=active_session.user_id,
                subject_id=active_session.subject_id,
                topic_id=active_session.topic_id,
                status=active_session.status,
                source=active_session.source,
                start_time=active_session.start_time,
                end_time=active_session.end_time,
                last_heartbeat_at=active_session.last_heartbeat_at,
                accumulated_active_seconds=active_session.accumulated_active_seconds,
                duration_minutes=active_session.accumulated_active_seconds // 60,
                target_duration_minutes=active_session.target_duration_minutes,
                focus_rating=active_session.focus_rating,
                reflection_note=active_session.reflection_note,
                subject_name=active_session.subject.name if active_session.subject else None,
                subject_code=active_session.subject.code if active_session.subject else None,
                topic_title=active_session.topic.title if active_session.topic else None,
            )

        return DashboardOverviewResponse(
            student_name=user.full_name,
            college_name=college.name if college else "VIT Pune",
            department_name=dept.name if dept else "Engineering",
            division_name=division.name if division else None,
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
            consistency_score=consistency_score,
            study_time_today_minutes=study_minutes_today,
            active_session=active_session_res,
            enrolled_subjects=enrolled_subjects,
            todays_schedule=schedule_slots,
            actionable_recommendation=rec,
        )

    async def get_system_metrics(self) -> SystemMetricsResponse:
        metrics_dict = await self.dashboard_repo.get_system_metrics()
        return SystemMetricsResponse(**metrics_dict)
