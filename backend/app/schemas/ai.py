import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AiStatusResponse(BaseModel):
    provider: str
    model: str
    configured: bool
    cache: str


class FlightBriefingRequest(BaseModel):
    subject_id: int
    topic_id: Optional[int] = None


class FlightBriefingResponse(BaseModel):
    cache_key: str
    subject_id: int
    subject_code: str
    subject_name: str
    topic_id: Optional[int] = None
    topic: Optional[str] = None
    title: str
    hook: str
    concepts: List[str]
    check_question: str
    recommended_minutes: int
    model: str
    generated_at: datetime
    cached: bool


class AiQuizRequest(BaseModel):
    subject_id: int
    topic_id: Optional[int] = None
    difficulty: Literal["easy", "mixed", "hard"] = "mixed"
    count: int = Field(default=5, ge=3, le=8)


class AiQuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer_index: int
    explanation: str


class AiQuizResponse(BaseModel):
    cache_key: str
    subject_id: int
    subject_code: str
    subject_name: str
    topic_id: Optional[int] = None
    topic: Optional[str] = None
    title: str
    questions: List[AiQuizQuestion]
    model: str
    generated_at: datetime
    cached: bool


class AiQuizAttemptRequest(BaseModel):
    id: uuid.UUID
    cache_key: str = Field(min_length=20, max_length=300)
    answers: List[int] = Field(min_length=3, max_length=8)


class AiQuizAttemptResponse(BaseModel):
    id: uuid.UUID
    subject_id: int
    score: int
    total: int
    created_at: datetime
