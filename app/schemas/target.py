from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(max_length=2048)
    interval_seconds: int = Field(default=60, ge=10)
    expected_status: int = Field(default=200, ge=100, le=599)
    tls_warning_days: int = Field(default=30, ge=0)
    version_url: str | None = Field(default=None, max_length=2048)
    enabled: bool = True

    @field_validator("url", "version_url")
    @classmethod
    def validate_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("must be an absolute http or https URL")
        return value


class TargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str
    interval_seconds: int
    expected_status: int
    tls_warning_days: int
    version_url: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
