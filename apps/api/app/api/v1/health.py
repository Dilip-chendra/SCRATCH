import time
from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.database import check_database_health
from app.schemas.health import HealthCheckResponse, ServiceStatus

router = APIRouter(tags=["Health"])


async def check_redis_health() -> tuple[bool, float, str]:
    """Execute PING on Redis to measure connectivity and latency."""
    start = time.perf_counter()
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        pong = await client.ping()
        await client.aclose()
        latency_ms = (time.perf_counter() - start) * 1000
        if pong:
            return True, round(latency_ms, 2), ""
        return False, 0.0, "Redis did not return PONG"
    except Exception:
        # Sanitize error to avoid leaking connection strings, hosts, or credentials
        return False, 0.0, "Redis connection failed"


@router.get("/health", response_model=HealthCheckResponse)
@router.get("/api/v1/health", response_model=HealthCheckResponse)
async def get_system_health(response: Response):
    """
    Live system health endpoint.
    Performs real live checks against PostgreSQL and Redis.
    Returns HTTP 200 if all services are healthy, or HTTP 503 if any service fails.
    """
    db_ok, db_latency = await check_database_health()
    redis_ok, redis_latency, redis_err = await check_redis_health()

    services = {
        "database": ServiceStatus(
            status="healthy" if db_ok else "unhealthy",
            latency_ms=db_latency,
            error=None if db_ok else "Database connection failed"
        ),
        "redis": ServiceStatus(
            status="healthy" if redis_ok else "unhealthy",
            latency_ms=redis_latency,
            error=None if redis_ok else redis_err
        ),
        "worker": ServiceStatus(
            status="healthy" if redis_ok else "degraded",
            latency_ms=redis_latency,
            error=None if redis_ok else "Worker broker unreachable"
        )
    }

    all_healthy = db_ok and redis_ok
    overall_status = "healthy" if all_healthy else "unhealthy"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheckResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        services=services
    )
