import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.session import StudySession
from app.models.student import User
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    CompleteSessionRequest,
    HeartbeatRequest,
    SessionResponse,
    SessionSummaryResponse,
    StartSessionRequest,
)
from app.services.session_service import SessionService

router = APIRouter()


def map_session_to_response(session: StudySession) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        subject_id=session.subject_id,
        topic_id=session.topic_id,
        status=session.status,
        source=session.source,
        start_time=session.start_time,
        end_time=session.end_time,
        last_heartbeat_at=session.last_heartbeat_at,
        accumulated_active_seconds=session.accumulated_active_seconds,
        duration_minutes=session.accumulated_active_seconds // 60,
        target_duration_minutes=session.target_duration_minutes,
        focus_rating=session.focus_rating,
        reflection_note=session.reflection_note,
        subject_name=session.subject.name if session.subject else None,
        subject_code=session.subject.code if session.subject else None,
        topic_title=session.topic.title if session.topic else None,
    )


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Starts an ACTIVE study session for the authenticated student.
    Auto-reconciles stale sessions before starting.
    """
    service = SessionService(db)
    session = await service.start_session(current_user.id, request)
    return map_session_to_response(session)


@router.get("/active", response_model=Optional[SessionResponse])
async def get_active_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the student's currently ACTIVE or PAUSED session, or null if idle.
    """
    repo = SessionRepository(db)
    session = await repo.get_active_or_paused_session(current_user.id)
    return map_session_to_response(session) if session else None


@router.post("/{session_id}/heartbeat", response_model=SessionResponse)
async def record_heartbeat(
    session_id: uuid.UUID,
    request: HeartbeatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Heartbeat ping from mobile or ESP32. Accumulates active study seconds.
    """
    service = SessionService(db)
    session = await service.record_heartbeat(current_user.id, session_id, request)
    return map_session_to_response(session)


@router.post("/{session_id}/pause", response_model=SessionResponse)
async def pause_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Transitions session from ACTIVE to PAUSED state.
    """
    service = SessionService(db)
    session = await service.pause_session(current_user.id, session_id)
    return map_session_to_response(session)


@router.post("/{session_id}/resume", response_model=SessionResponse)
async def resume_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Transitions session from PAUSED back to ACTIVE state.
    """
    service = SessionService(db)
    session = await service.resume_session(current_user.id, session_id)
    return map_session_to_response(session)


@router.post("/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    request: CompleteSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Concludes the study session with focus rating and qualitative reflection.
    Atomically updates total study time, running focus averages, and streaks.
    """
    service = SessionService(db)
    session = await service.complete_session(current_user.id, session_id, request)
    return map_session_to_response(session)


@router.post("/{session_id}/abandon", response_model=SessionResponse)
async def abandon_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks an active or paused session as ABANDONED without counting toward streaks.
    """
    service = SessionService(db)
    session = await service.abandon_session(current_user.id, session_id)
    return map_session_to_response(session)


@router.get("/{session_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Future AI Hook: Returns formatted session telemetry ready for Gemini analysis.
    """
    service = SessionService(db)
    return await service.build_session_summary(session_id)
