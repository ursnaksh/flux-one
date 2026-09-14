from fastapi import APIRouter

from app.api.v1.endpoints import auth, dashboard, institution, sessions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Study Sessions"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(institution.router, prefix="/institution", tags=["Institution Catalog"])
