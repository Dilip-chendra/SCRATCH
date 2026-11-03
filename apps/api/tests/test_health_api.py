from unittest.mock import patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_structure(client: AsyncClient):
    """Verify that the health check endpoint returns valid JSON structure and service status."""
    response = await client.get("/health")
    assert response.status_code in (200, 503)

    data = response.json()
    assert "status" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert "worker" in data["services"]


@pytest.mark.asyncio
async def test_health_endpoint_returns_503_on_dependency_failure(client: AsyncClient):
    """Verify that a failing database connection triggers HTTP 503 Service Unavailable."""
    with patch("app.api.v1.health.check_database_health", return_value=(False, 0.0)):
        response = await client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["services"]["database"]["status"] == "unhealthy"
