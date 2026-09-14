from typing import List, Optional
from app.models.session import StudySession
from app.schemas.auth import SubjectSimpleResponse


class RecommendationService:
    """
    Dedicated domain service responsible for generating actionable study nudges.
    Decoupled from DashboardService so rules or future Gemini reasoning can evolve independently.
    """
    @staticmethod
    def get_daily_nudge(
        active_session: Optional[StudySession],
        current_streak: int,
        study_minutes_today: int,
        enrolled_subjects: List[SubjectSimpleResponse],
    ) -> str:
        if active_session:
            subject_name = active_session.subject.name if active_session.subject else "your course"
            return f"Active session in progress on {subject_name}. Stay focused!"

        if current_streak > 0 and study_minutes_today < 20:
            return f"Keep your {current_streak}-day streak alive! Complete a 20-minute study block today."

        if study_minutes_today >= 45:
            return f"Solid consistency today! You have logged {study_minutes_today} minutes of focused study."

        if enrolled_subjects:
            first_subject = enrolled_subjects[0].name
            return f"Ready to start? Begin a study session on '{first_subject}' to advance your consistency."

        return "Welcome to FLUX ONE! Select your subjects to begin tracking your academic growth."
