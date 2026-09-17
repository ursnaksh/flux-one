from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.student import User
from app.schemas.ai import (
    AiQuizAttemptRequest,
    AiQuizAttemptResponse,
    AiQuizRequest,
    AiQuizResponse,
    AiStatusResponse,
    FlightBriefingRequest,
    FlightBriefingResponse,
)
from app.services.ai_service import (
    AiAccessError,
    AiConfigurationError,
    AiInputError,
    AiOutputError,
    AiProviderError,
    generate_ai_quiz,
    generate_flight_briefing,
    get_ai_status,
    save_ai_quiz_attempt,
)


router = APIRouter()


def _translate_ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AiAccessError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    if isinstance(exc, AiInputError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, AiConfigurationError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if isinstance(exc, (AiProviderError, AiOutputError)):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="AI request failed unexpectedly.",
    )


@router.get("/status", response_model=AiStatusResponse)
async def ai_status(
    _: User = Depends(get_current_user),
):
    return get_ai_status()


@router.post(
    "/flight-briefing",
    response_model=FlightBriefingResponse,
)
async def flight_briefing(
    request: FlightBriefingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await generate_flight_briefing(db, current_user, request)
    except (
        AiAccessError,
        AiInputError,
        AiConfigurationError,
        AiProviderError,
        AiOutputError,
    ) as exc:
        raise _translate_ai_error(exc) from exc


@router.post(
    "/quiz",
    response_model=AiQuizResponse,
)
async def ai_quiz(
    request: AiQuizRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await generate_ai_quiz(db, current_user, request)
    except (
        AiAccessError,
        AiInputError,
        AiConfigurationError,
        AiProviderError,
        AiOutputError,
    ) as exc:
        raise _translate_ai_error(exc) from exc


@router.post(
    "/quiz-attempts",
    response_model=AiQuizAttemptResponse,
)
async def ai_quiz_attempt(
    request: AiQuizAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await save_ai_quiz_attempt(db, current_user, request)
    except (
        AiAccessError,
        AiInputError,
        AiConfigurationError,
        AiProviderError,
        AiOutputError,
    ) as exc:
        raise _translate_ai_error(exc) from exc
