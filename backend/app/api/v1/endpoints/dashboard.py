from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.student import User
from app.schemas.dashboard import DashboardOverviewResponse, SystemMetricsResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Consolidated Single-Call Dashboard Overview:
    Aggregates profile, streak, daily study minutes, active session, enrolled subjects,
    today's scheduled lectures, and contextual recommendations in one roundtrip.
    """
    service = DashboardService(db)
    return await service.get_student_dashboard(current_user.id)


@router.get("/internal/metrics", response_model=SystemMetricsResponse)
async def get_internal_metrics(db: AsyncSession = Depends(get_db)):
    """
    Operational Telemetry Endpoint:
    Returns system-wide aggregated telemetry for observability and operational debugging.
    """
    service = DashboardService(db)
    return await service.get_system_metrics()
