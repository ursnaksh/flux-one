import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_admin_secret
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, get_db
from app.core.logging import logger, setup_logging
from app.schemas.dashboard import SystemMetricsResponse
from app.services.dashboard_service import DashboardService

SERVER_START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Initializing FLUX ONE Core API...", extra={"request_id": "startup"})
    yield
    logger.info("Disposing database connection pools...", extra={"request_id": "shutdown"})
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Serve the upgraded FLUX ONE student website at root (/)
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    for candidate in ["index.html", "backend/index.html", "../index.html"]:
        if os.path.exists(candidate):
            return FileResponse(candidate)
    return HTMLResponse("<h2>FLUX ONE API is running. Documentation: <a href='/api/v1/docs'>/api/v1/docs</a></h2>")

@app.get("/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)):
    uptime = round(time.time() - SERVER_START_TIME, 2)
    db_status = "down"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "up"
    except Exception as e:
        logger.error(f"Health check failed database ping: {e}", extra={"request_id": "health"})
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "down", "version": settings.VERSION, "uptime_seconds": uptime, "error": "Database connectivity check failed"},
        )
    return {"status": "healthy", "database": db_status, "version": settings.VERSION, "uptime_seconds": uptime}

@app.get("/internal/metrics", response_model=SystemMetricsResponse, tags=["Observability"])
async def get_internal_metrics(_authorized: bool = Depends(verify_admin_secret), db: AsyncSession = Depends(get_db)):
    service = DashboardService(db)
    return await service.get_system_metrics()
