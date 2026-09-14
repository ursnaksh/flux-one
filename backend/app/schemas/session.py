import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import SessionSource, SessionStatus


class StartSessionRequest(BaseModel):
    subject_id: int
    topic_id: Optional[int] = None
    target_duration_minutes: Optional[int] = Field(default=45, ge=5, le=360)
    source: SessionSource = SessionSource.MOBILE


class HeartbeatRequest(BaseModel):
    client_timestamp: Optional[datetime] = None


class CompleteSessionRequest(BaseModel):
    focus_rating: int = Field(ge=1, le=5, description="Focus rating from 1 to 5")
    reflection_note: Optional[str] = Field(default=None, max_length=2000)


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    subject_id: int
    topic_id: Optional[int] = None
    status: SessionStatus
    source: SessionSource
    start_time: datetime
    end_time: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    accumulated_active_seconds: int
    duration_minutes: int
    target_duration_minutes: Optional[int] = None
    focus_rating: Optional[int] = None
    reflection_note: Optional[str] = None
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    topic_title: Optional[str] = None

    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    session_id: uuid.UUID
    subject_name: str
    subject_code: str
    topic_title: Optional[str] = None
    duration_minutes: int
    focus_rating: Optional[int] = None
    reflection_note: Optional[str] = None
    completed_at: datetime
    student_total_study_minutes: int
    student_current_streak: int

    class Config:
        from_attributes = True
