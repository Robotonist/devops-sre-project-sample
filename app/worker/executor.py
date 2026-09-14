from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.target import Target
from app.probes.service import ProbeOutcome, run_probe

ProbeRunner = Callable[[Target], ProbeOutcome]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def execute_target_check(
    db: Session,
    target_id: UUID,
    *,
    probe_runner: ProbeRunner = run_probe,
) -> UUID | None:
    target = db.get(Target, target_id)
    if target is None:
        return None

    started_at = utc_now()
    outcome = probe_runner(target)
    completed_at = utc_now()

    result = CheckResult(
        target_id=target.id,
        started_at=started_at,
        completed_at=completed_at,
        status=outcome.status,
        http_status=outcome.http_status,
        latency_ms=outcome.latency_ms,
        tls_valid=outcome.tls_valid,
        tls_expires_at=outcome.tls_expires_at,
        tls_days_remaining=outcome.tls_days_remaining,
        version=outcome.version,
        error_type=outcome.error_type,
        error_message=outcome.error_message,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result.id
