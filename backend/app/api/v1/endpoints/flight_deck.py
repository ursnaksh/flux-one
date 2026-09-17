from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.student import User
from app.schemas.flight_deck import FlightDeckTodayResponse
from app.services.flight_deck_service import get_today_flight_deck


router = APIRouter()


@router.get(
    "/today",
    response_model=FlightDeckTodayResponse,
)
async def today_flight_deck(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_today_flight_deck(
            db=db,
            user=current_user,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    