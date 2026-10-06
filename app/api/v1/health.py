"""Health check probe endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.envelope import ResponseItemEnvelope

router = APIRouter(tags=["Health"])


class HealthStatus(BaseModel):
    """Payload schema for health status probe."""

    status: str = Field(default="healthy", description="Current service health status")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the health check",
    )
    version: str = Field(default="1.0.0", description="Service release version")
    service: str = Field(default="BiteRoute API", description="Service name")

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/health",
    response_model=ResponseItemEnvelope[HealthStatus],
    summary="Health check probe",
    description="Service liveness probe returning system status, timestamp, and version.",
)
async def get_health_v1() -> ResponseItemEnvelope[HealthStatus]:
    """Return healthy service status."""
    return ResponseItemEnvelope(data=HealthStatus())
