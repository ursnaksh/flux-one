import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.enums import EnrollmentStatus
from app.models.institution import Subject, Topic
from app.models.student import Enrollment, User
from app.schemas.ai import (
    AiQuizAttemptRequest,
    AiQuizAttemptResponse,
    AiQuizRequest,
    AiQuizResponse,
    AiStatusResponse,
    FlightBriefingRequest,
    FlightBriefingResponse,
)


class AiInputError(Exception):
    pass


class AiAccessError(Exception):
    pass


class AiConfigurationError(Exception):
    pass


class AiProviderError(Exception):
    pass


class AiOutputError(Exception):
    pass


class _BriefingPayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    hook: str = Field(min_length=1, max_length=1000)
    concepts: list[str] = Field(min_length=3, max_length=5)
    check_question: str = Field(min_length=1, max_length=500)
    recommended_minutes: int = Field(ge=3, le=5)


class _QuizQuestionPayload(BaseModel):
    question: str = Field(min_length=1, max_length=600)
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explanation: str = Field(min_length=1, max_length=600)


class _QuizPayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    questions: list[_QuizQuestionPayload]


BRIEFING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "concepts": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 5,
        },
        "check_question": {"type": "string"},
        "recommended_minutes": {"type": "integer", "minimum": 3, "maximum": 5},
    },
    "required": [
        "title",
        "hook",
        "concepts",
        "check_question",
        "recommended_minutes",
    ],
}


def _quiz_schema(count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "questions": {
                "type": "array",
                "minItems": count,
                "maxItems": count,
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 4,
                            "maxItems": 4,
                        },
                        "answer_index": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3,
                        },
                        "explanation": {"type": "string"},
                    },
                    "required": [
                        "question",
                        "options",
                        "answer_index",
                        "explanation",
                    ],
                },
            },
        },
        "required": ["title", "questions"],
    }


def get_ai_status() -> AiStatusResponse:
    return AiStatusResponse(
        provider="Google Gemini",
        model=settings.GEMINI_MODEL,
        configured=bool(settings.GEMINI_API_KEY.strip()),
        cache="database",
    )


async def _academic_context(
    db: AsyncSession,
    user: User,
    subject_id: int,
    topic_id: Optional[int],
) -> tuple[Subject, Optional[Topic]]:
    stmt = (
        select(Subject)
        .join(Enrollment, Enrollment.subject_id == Subject.id)
        .options(selectinload(Subject.topics))
        .where(
            Subject.id == subject_id,
            Enrollment.user_id == user.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    result = await db.execute(stmt)
    subject = result.scalar_one_or_none()
    if subject is None:
        raise AiAccessError("Choose a subject from your active enrollments.")

    topic = None
    if topic_id is not None:
        topic = next((item for item in subject.topics if item.id == topic_id), None)
        if topic is None:
            raise AiInputError("Choose a verified topic that belongs to this subject.")

    return subject, topic


def _context_text(subject: Subject, topic: Optional[Topic]) -> str:
    verified_topics = sorted(
        subject.topics,
        key=lambda item: (item.unit_number, item.id),
    )
    topic_lines = [
        f"Unit {item.unit_number}: {item.title}"
        + (f" — {item.description}" if item.description else "")
        for item in verified_topics
    ]
    selected = (
        f"Selected verified topic: Unit {topic.unit_number}: {topic.title}."
        if topic
        else "No specific topic is mapped for this request. Stay at subject level and do not invent a current lecture topic."
    )
    catalog = (
        "Verified syllabus topics:\n- " + "\n- ".join(topic_lines)
        if topic_lines
        else "No verified syllabus topics are stored yet. Do not invent syllabus coverage."
    )
    return (
        f"Subject: {subject.name} ({subject.code}).\n"
        f"{selected}\n"
        f"{catalog}"
    )


def _cache_key(
    kind: str,
    subject: Subject,
    topic: Optional[Topic],
    context_text: str,
    suffix: str = "",
) -> str:
    digest = hashlib.sha256(
        f"{settings.GEMINI_MODEL}|{context_text}|{suffix}".encode("utf-8")
    ).hexdigest()[:24]
    return (
        f"ai:v2:{kind}:subject:{subject.id}:topic:{topic.id if topic else 'none'}:"
        f"{digest}"
    )


async def _read_cache(
    db: AsyncSession,
    cache_key: str,
    kind: str,
) -> Optional[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        text(
            """
            SELECT response_json, model, created_at
            FROM ai_cache
            WHERE cache_key = :cache_key
              AND kind = :kind
              AND expires_at > :now
            """
        ),
        {"cache_key": cache_key, "kind": kind, "now": now},
    )
    row = result.mappings().first()
    if row is None:
        return None
    try:
        payload = json.loads(row["response_json"])
    except (TypeError, json.JSONDecodeError):
        return None
    return {
        "payload": payload,
        "model": row["model"],
        "generated_at": row["created_at"],
    }


async def _write_cache(
    db: AsyncSession,
    *,
    cache_key: str,
    kind: str,
    subject_id: int,
    topic_id: Optional[int],
    payload: dict[str, Any],
    ttl: timedelta,
) -> datetime:
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + ttl
    await db.execute(
        text(
            """
            INSERT INTO ai_cache (
                cache_key, kind, model, subject_id, topic_id,
                response_json, created_at, expires_at
            ) VALUES (
                :cache_key, :kind, :model, :subject_id, :topic_id,
                :response_json, :created_at, :expires_at
            )
            ON CONFLICT (cache_key) DO UPDATE SET
                kind = EXCLUDED.kind,
                model = EXCLUDED.model,
                subject_id = EXCLUDED.subject_id,
                topic_id = EXCLUDED.topic_id,
                response_json = EXCLUDED.response_json,
                created_at = EXCLUDED.created_at,
                expires_at = EXCLUDED.expires_at
            """
        ),
        {
            "cache_key": cache_key,
            "kind": kind,
            "model": settings.GEMINI_MODEL,
            "subject_id": subject_id,
            "topic_id": topic_id,
            "response_json": json.dumps(payload, ensure_ascii=False),
            "created_at": created_at,
            "expires_at": expires_at,
        },
    )
    await db.commit()
    return created_at


async def _call_gemini(
    *,
    prompt: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key:
        raise AiConfigurationError(
            "AI is not configured yet. Add GEMINI_API_KEY to the server environment."
        )

    model = settings.GEMINI_MODEL.strip()
    endpoint_template = settings.GEMINI_API_ENDPOINT.strip()
    endpoint = endpoint_template.replace("{model}", quote(model, safe=""))

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key,
                },
                json=body,
            )
    except httpx.TimeoutException as exc:
        raise AiProviderError("Gemini took too long to respond. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise AiProviderError("Gemini could not be reached. Please retry.") from exc

    if response.status_code in (401, 403):
        raise AiConfigurationError(
            "Gemini rejected the server key. Check GEMINI_API_KEY in the deployment environment."
        )
    if response.status_code == 429:
        raise AiProviderError("Gemini rate limit reached. Try again in a moment.")
    if not response.is_success:
        raise AiProviderError(
            f"Gemini returned an upstream error ({response.status_code})."
        )

    try:
        provider_payload = response.json()
    except ValueError as exc:
        raise AiProviderError("Gemini returned an unreadable response.") from exc

    parts = (
        provider_payload.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    response_text = "".join(
        str(part.get("text", ""))
        for part in parts
        if isinstance(part, dict)
    ).strip()
    if not response_text:
        raise AiOutputError("Gemini returned no generated content.")

    if response_text.startswith("```"):
        response_text = response_text.strip("`").strip()
        if response_text.lower().startswith("json"):
            response_text = response_text[4:].strip()

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise AiOutputError("Gemini returned malformed JSON.") from exc
    if not isinstance(parsed, dict):
        raise AiOutputError("Gemini returned an invalid structured response.")
    return parsed


def _validate_briefing(payload: dict[str, Any]) -> _BriefingPayload:
    try:
        value = _BriefingPayload.model_validate(payload)
    except ValidationError as exc:
        raise AiOutputError("Gemini returned an invalid briefing.") from exc
    if any(not item.strip() for item in value.concepts):
        raise AiOutputError("Gemini returned an invalid concept list.")
    return value


def _validate_quiz(payload: dict[str, Any], count: int) -> _QuizPayload:
    try:
        value = _QuizPayload.model_validate(payload)
    except ValidationError as exc:
        raise AiOutputError("Gemini returned an invalid quiz.") from exc
    if len(value.questions) != count:
        raise AiOutputError("Gemini returned the wrong number of quiz questions.")
    for question in value.questions:
        normalized = [option.strip().casefold() for option in question.options]
        if any(not option for option in normalized) or len(set(normalized)) != 4:
            raise AiOutputError("Gemini returned duplicate or empty quiz options.")
    return value


async def generate_flight_briefing(
    db: AsyncSession,
    user: User,
    request: FlightBriefingRequest,
) -> FlightBriefingResponse:
    subject, topic = await _academic_context(
        db,
        user,
        request.subject_id,
        request.topic_id,
    )
    context = _context_text(subject, topic)
    cache_key = _cache_key("flight_briefing", subject, topic, context)

    cached = await _read_cache(db, cache_key, "flight_briefing")
    if cached:
        briefing = _validate_briefing(cached["payload"])
        return FlightBriefingResponse(
            cache_key=cache_key,
            subject_id=subject.id,
            subject_code=subject.code,
            subject_name=subject.name,
            topic_id=topic.id if topic else None,
            topic=topic.title if topic else None,
            **briefing.model_dump(),
            model=cached["model"],
            generated_at=cached["generated_at"],
            cached=True,
        )

    prompt = (
        "You are FLUX ONE, a concise academic copilot for engineering students.\n"
        "Create a 3-to-5 minute pre-class briefing using ONLY the verified academic context below.\n"
        "Do not invent a lecture topic, syllabus unit, timetable fact, assessment, professor instruction, or student performance.\n"
        "If no specific topic is mapped, keep the briefing at subject level and say nothing that implies a particular topic is being taught now.\n"
        "Return JSON matching the supplied schema. Make the concepts practical and the check question answerable from the briefing.\n\n"
        f"{context}"
    )
    raw = await _call_gemini(prompt=prompt, schema=BRIEFING_SCHEMA)
    briefing = _validate_briefing(raw)
    generated_at = await _write_cache(
        db,
        cache_key=cache_key,
        kind="flight_briefing",
        subject_id=subject.id,
        topic_id=topic.id if topic else None,
        payload=briefing.model_dump(),
        ttl=timedelta(hours=24),
    )
    return FlightBriefingResponse(
        cache_key=cache_key,
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        topic_id=topic.id if topic else None,
        topic=topic.title if topic else None,
        **briefing.model_dump(),
        model=settings.GEMINI_MODEL,
        generated_at=generated_at,
        cached=False,
    )


async def generate_ai_quiz(
    db: AsyncSession,
    user: User,
    request: AiQuizRequest,
) -> AiQuizResponse:
    subject, topic = await _academic_context(
        db,
        user,
        request.subject_id,
        request.topic_id,
    )
    context = _context_text(subject, topic)
    suffix = f"difficulty={request.difficulty}|count={request.count}"
    cache_key = _cache_key("quiz", subject, topic, context, suffix)

    cached = await _read_cache(db, cache_key, "quiz")
    if cached:
        quiz = _validate_quiz(cached["payload"], request.count)
        return AiQuizResponse(
            cache_key=cache_key,
            subject_id=subject.id,
            subject_code=subject.code,
            subject_name=subject.name,
            topic_id=topic.id if topic else None,
            topic=topic.title if topic else None,
            **quiz.model_dump(),
            model=cached["model"],
            generated_at=cached["generated_at"],
            cached=True,
        )

    prompt = (
        "You are FLUX ONE, an engineering-course quiz author.\n"
        f"Create exactly {request.count} multiple-choice questions at {request.difficulty} difficulty.\n"
        "Use ONLY the verified academic context below. Do not invent syllabus coverage or content from another subject.\n"
        "Each question must have exactly four distinct options, one unambiguous correct answer, and a short explanation.\n"
        "Return JSON matching the supplied schema and no markdown.\n\n"
        f"{context}"
    )
    raw = await _call_gemini(prompt=prompt, schema=_quiz_schema(request.count))
    quiz = _validate_quiz(raw, request.count)
    generated_at = await _write_cache(
        db,
        cache_key=cache_key,
        kind="quiz",
        subject_id=subject.id,
        topic_id=topic.id if topic else None,
        payload=quiz.model_dump(),
        ttl=timedelta(days=7),
    )
    return AiQuizResponse(
        cache_key=cache_key,
        subject_id=subject.id,
        subject_code=subject.code,
        subject_name=subject.name,
        topic_id=topic.id if topic else None,
        topic=topic.title if topic else None,
        **quiz.model_dump(),
        model=settings.GEMINI_MODEL,
        generated_at=generated_at,
        cached=False,
    )


async def save_ai_quiz_attempt(
    db: AsyncSession,
    user: User,
    request: AiQuizAttemptRequest,
) -> AiQuizAttemptResponse:
    existing_result = await db.execute(
        text(
            """
            SELECT id, subject_id, score, total, created_at, user_id
            FROM ai_quiz_attempts
            WHERE id = :attempt_id
            """
        ),
        {"attempt_id": request.id},
    )
    existing = existing_result.mappings().first()
    if existing:
        if existing["user_id"] != user.id:
            raise AiInputError("That quiz attempt ID is already in use.")
        return AiQuizAttemptResponse(
            id=existing["id"],
            subject_id=existing["subject_id"],
            score=existing["score"],
            total=existing["total"],
            created_at=existing["created_at"],
        )

    now = datetime.now(timezone.utc)
    cache_result = await db.execute(
        text(
            """
            SELECT subject_id, response_json
            FROM ai_cache
            WHERE cache_key = :cache_key
              AND kind = 'quiz'
              AND expires_at > :now
            """
        ),
        {"cache_key": request.cache_key, "now": now},
    )
    cached = cache_result.mappings().first()
    if cached is None:
        raise AiInputError("That AI quiz is no longer available. Generate it again.")

    await _academic_context(db, user, cached["subject_id"], None)

    try:
        quiz = _QuizPayload.model_validate(json.loads(cached["response_json"]))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AiInputError("That AI quiz is invalid. Generate it again.") from exc

    if len(request.answers) != len(quiz.questions):
        raise AiInputError("Provide one answer for every quiz question.")
    if any(answer < 0 or answer > 3 for answer in request.answers):
        raise AiInputError("Quiz answers must be option indexes from 0 to 3.")

    score = sum(
        1
        for index, answer in enumerate(request.answers)
        if answer == quiz.questions[index].answer_index
    )
    await db.execute(
        text(
            """
            INSERT INTO ai_quiz_attempts (
                id, user_id, subject_id, cache_key,
                answers_json, score, total, created_at
            ) VALUES (
                :id, :user_id, :subject_id, :cache_key,
                :answers_json, :score, :total, :created_at
            )
            """
        ),
        {
            "id": request.id,
            "user_id": user.id,
            "subject_id": cached["subject_id"],
            "cache_key": request.cache_key,
            "answers_json": json.dumps(request.answers),
            "score": score,
            "total": len(quiz.questions),
            "created_at": now,
        },
    )
    await db.commit()
    return AiQuizAttemptResponse(
        id=request.id,
        subject_id=cached["subject_id"],
        score=score,
        total=len(quiz.questions),
        created_at=now,
    )
