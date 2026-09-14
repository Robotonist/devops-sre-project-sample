from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_id: UUID
    started_at: datetime
    completed_at: datetime
    status: str
    http_status: int | None
    latency_ms: float | None
    tls_valid: bool | None
    tls_expires_at: datetime | None
    tls_days_remaining: int | None
    version: str | None
    error_type: str | None
    error_message: str | None
