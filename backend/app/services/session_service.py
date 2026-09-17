import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import EnrollmentStatus, SessionSource, SessionStatus
from app.models.institution import Topic
from app.models.student import Enrollment
from app.models.session import StudySession
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    CompleteSessionRequest,
    HeartbeatRequest,
    SessionResponse,
    SessionSummaryResponse,
    StartSessionRequest,
)

MINIMUM_STREAK_QUALIFYING_MINUTES = 20
STALE_SESSION_THRESHOLD_SECONDS = 7200  # 2 hours without heartbeat


class SessionService:
    """
    Domain service governing the Study Session State Machine and atomic discipline statistics.
    Enforces all state transitions and business rules.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SessionRepository(db)

    async def reconcile_active_sessions(self, user_id: uuid.UUID) -> None:
        """
        Single place for stale session resolution.
        If an active session exists and its heartbeat is stale (>2 hours), marks it ABANDONED.
        If an active session exists and is fresh, raises 400 Bad Request.
        """
        active_session = await self.repo.get_active_or_paused_session(user_id)
        if not active_session:
            return

        now = datetime.now(timezone.utc)
        reference_time = active_session.last_heartbeat_at or active_session.start_time
        idle_seconds = (now - reference_time).total_seconds()

        if idle_seconds > STALE_SESSION_THRESHOLD_SECONDS:
            # Auto-abandon stale session while preserving logged study seconds
            active_session.status = SessionStatus.ABANDONED
            active_session.end_time = reference_time
            await self.repo.save_session(active_session)
            await self.db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An active study session ({active_session.status.value}) is already in progress.",
            )

    async def start_session(self, user_id: uuid.UUID, request: StartSessionRequest) -> StudySession:
        """
        Initiates a study session in ACTIVE state after running auto-reconciliation.
        """
        await self.reconcile_active_sessions(user_id)

        enrollment_result = await self.db.execute(
            select(Enrollment.id).where(
                Enrollment.user_id == user_id,
                Enrollment.subject_id == request.subject_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
        )
        if enrollment_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not actively enrolled in the selected subject.",
            )

        if request.topic_id is not None:
            topic_result = await self.db.execute(
                select(Topic.id).where(
                    Topic.id == request.topic_id,
                    Topic.subject_id == request.subject_id,
                )
            )
            if topic_result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The selected topic does not belong to this subject.",
                )

        now = datetime.now(timezone.utc)
        session = StudySession(
            user_id=user_id,
            subject_id=request.subject_id,
            topic_id=request.topic_id,
            status=SessionStatus.ACTIVE,
            source=request.source,
            start_time=now,
            last_heartbeat_at=now,
            accumulated_active_seconds=0,
            target_duration_minutes=request.target_duration_minutes,
        )

        saved = await self.repo.save_session(session)
        await self.db.commit()
        return await self.repo.get_by_id(saved.id)

    async def record_heartbeat(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: HeartbeatRequest,
    ) -> StudySession:
        """
        Accumulates active study seconds based on heartbeat intervals.
        Does not accumulate time if the session is currently PAUSED.
        """
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found.")

        if session.status == SessionStatus.PAUSED:
            return session  # Heartbeat received while paused: no active time accumulated

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record heartbeat on session in {session.status.value} state.",
            )

        now = datetime.now(timezone.utc)
        last_hb = session.last_heartbeat_at or session.start_time
        delta_seconds = int((now - last_hb).total_seconds())

        # Cap delta to 5 minutes to guard against anomalous client clock jumps
        capped_delta = max(0, min(delta_seconds, 300))
        session.accumulated_active_seconds += capped_delta
        session.last_heartbeat_at = now

        await self.repo.save_session(session)
        await self.db.commit()
        return session

    async def pause_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> StudySession:
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found.")

        if session.status != SessionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause session in {session.status.value} state. Must be ACTIVE.",
            )

        now = datetime.now(timezone.utc)
        last_hb = session.last_heartbeat_at or session.start_time
        delta_seconds = int((now - last_hb).total_seconds())
        capped_delta = max(0, min(delta_seconds, 300))

        session.accumulated_active_seconds += capped_delta
        session.last_heartbeat_at = now
        session.status = SessionStatus.PAUSED

        await self.repo.save_session(session)
        await self.db.commit()
        return session

    async def resume_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> StudySession:
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found.")

        if session.status != SessionStatus.PAUSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume session in {session.status.value} state. Must be PAUSED.",
            )

        now = datetime.now(timezone.utc)
        session.last_heartbeat_at = now
        session.status = SessionStatus.ACTIVE

        await self.repo.save_session(session)
        await self.db.commit()
        return session

    async def complete_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        request: CompleteSessionRequest,
    ) -> StudySession:
        """
        Completes the study session and atomically updates discipline metrics (Streak & AcademicBrain).
        Streak increments strictly if session duration >= 20 mins and is the first qualifying session today.
        """
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found.")

        if session.status not in (SessionStatus.ACTIVE, SessionStatus.PAUSED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete session in {session.status.value} state.",
            )

        now = datetime.now(timezone.utc)

        # Accumulate final active chunk if completed directly from ACTIVE
        if session.status == SessionStatus.ACTIVE:
            last_hb = session.last_heartbeat_at or session.start_time
            delta_seconds = int((now - last_hb).total_seconds())
            capped_delta = max(0, min(delta_seconds, 300))
            session.accumulated_active_seconds += capped_delta

        session.status = SessionStatus.COMPLETED
        session.end_time = now
        session.focus_rating = request.focus_rating
        session.reflection_note = request.reflection_note

        try:
            # 1. Update Academic Brain
            duration_minutes = session.accumulated_active_seconds // 60
            brain = await self.repo.get_user_academic_brain(user_id)
            if brain:
                brain.total_study_minutes += duration_minutes
                if brain.average_focus_rating == 0.0:
                    brain.average_focus_rating = float(request.focus_rating)
                else:
                    brain.average_focus_rating = round(
                        (brain.average_focus_rating * 0.8) + (request.focus_rating * 0.2), 2
                    )
                brain.last_ai_update = now

            # 2. Update Streak (Strict Qualifying Rule)
            streak = await self.repo.get_user_streak(user_id)
            if streak and duration_minutes >= MINIMUM_STREAK_QUALIFYING_MINUTES:
                today = now.date()
                last_date = streak.last_study_date.date() if streak.last_study_date else None

                if last_date != today:
                    # First qualifying session of the day
                    if last_date == today - timedelta(days=1):
                        streak.current_streak += 1
                    else:
                        streak.current_streak = 1

                    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
                    streak.last_study_date = now

            await self.repo.save_session(session)
            await self.db.commit()
            return session

        except Exception:
            await self.db.rollback()
            raise

    async def abandon_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> StudySession:
        session = await self.repo.get_by_id(session_id)
        if not session or session.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found.")

        if session.status in (SessionStatus.COMPLETED, SessionStatus.ABANDONED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session is already {session.status.value}.",
            )

        now = datetime.now(timezone.utc)
        session.status = SessionStatus.ABANDONED
        session.end_time = now

        await self.repo.save_session(session)
        await self.db.commit()
        return session

    async def build_session_summary(self, session_id: uuid.UUID) -> SessionSummaryResponse:
        """
        Future AI Hook: Produces structured session telemetry ready for Gemini analysis.
        """
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study session not found.")

        brain = await self.repo.get_user_academic_brain(session.user_id)
        streak = await self.repo.get_user_streak(session.user_id)

        return SessionSummaryResponse(
            session_id=session.id,
            subject_name=session.subject.name,
            subject_code=session.subject.code,
            topic_title=session.topic.title if session.topic else None,
            duration_minutes=session.accumulated_active_seconds // 60,
            focus_rating=session.focus_rating,
            reflection_note=session.reflection_note,
            completed_at=session.end_time or session.start_time,
            student_total_study_minutes=brain.total_study_minutes if brain else 0,
            student_current_streak=streak.current_streak if streak else 0,
        )
