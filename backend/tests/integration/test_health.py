import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from app.main import app
from app.core.database import get_db


@pytest.mark.asyncio
async def test_health_check_database_up():
    mock_db = AsyncMock()
    mock_result = AsyncMock()
    mock_result.scalar.return_value = 1
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "up"
        assert "uptime_seconds" in data
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time-MS" in response.headers

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check_database_down():
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("Database connection failure")

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "down"

    app.dependency_overrides.clear()
