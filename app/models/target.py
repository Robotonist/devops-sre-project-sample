from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_status: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    tls_warning_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    version_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
