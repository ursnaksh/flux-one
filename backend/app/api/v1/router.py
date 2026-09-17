from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    auth,
    dashboard,
    institution,
    sessions,
    flight_deck,
    student_content,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Study Sessions"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(institution.router, prefix="/institution", tags=["Institution Catalog"])
api_router.include_router(
    flight_deck.router,
    prefix="/flight-deck",
    tags=["Flight Deck"],
)
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI Academic Copilot"],
)
api_router.include_router(
    student_content.router,
    prefix="/student-data",
    tags=["Student Data"],
)
