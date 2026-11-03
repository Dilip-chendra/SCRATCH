from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str  # "healthy" | "unhealthy"
    latency_ms: float
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    environment: str
    timestamp: datetime
    services: Dict[str, ServiceStatus]
