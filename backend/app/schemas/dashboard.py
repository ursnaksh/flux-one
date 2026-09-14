from datetime import time
from typing import List, Optional
from pydantic import BaseModel
from app.schemas.auth import SubjectSimpleResponse
from app.schemas.session import SessionResponse


class TodayScheduleSlot(BaseModel):
    subject_name: str
    subject_code: str
    start_time: time
    end_time: time
    location: str
    instructor_name: Optional[str] = None

    class Config:
        from_attributes = True


class DashboardOverviewResponse(BaseModel):
    student_name: str
    college_name: str
    department_name: str
    division_name: Optional[str] = None

    # Aggregated Discipline & Streak
    current_streak_days: int
    longest_streak_days: int
    consistency_score: float
    study_time_today_minutes: int

    # Active State
    active_session: Optional[SessionResponse] = None

    # Curriculum & Schedule
    enrolled_subjects: List[SubjectSimpleResponse] = []
    todays_schedule: List[TodayScheduleSlot] = []

    # Proactive Rule-Based / Contextual Recommendation
    actionable_recommendation: str


class SystemMetricsResponse(BaseModel):
    total_registered_users: int
    active_sessions_now: int
    sessions_completed_today: int
    study_minutes_today: int
    global_average_focus: float
