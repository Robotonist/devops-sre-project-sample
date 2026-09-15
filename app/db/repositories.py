from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.check_result import CheckResult
from app.models.target import Target
from app.schemas.target import TargetCreate


def create_target(db: Session, payload: TargetCreate) -> Target:
    target = Target(**payload.model_dump())
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def list_targets(db: Session) -> list[Target]:
    return list(db.scalars(select(Target).order_by(Target.created_at)).all())


def get_target(db: Session, target_id: UUID) -> Target | None:
    return db.get(Target, target_id)


def list_check_results(db: Session, target_id: UUID) -> list[CheckResult]:
    statement = (
        select(CheckResult)
        .where(CheckResult.target_id == target_id)
        .order_by(CheckResult.started_at.desc())
    )
    return list(db.scalars(statement).all())


def list_due_targets(
    db: Session,
    *,
    now: datetime | None = None,
) -> list[Target]:
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    latest_check = (
        select(
            CheckResult.target_id.label("target_id"),
            func.max(CheckResult.started_at).label("last_started_at"),
        )
        .group_by(CheckResult.target_id)
        .subquery()
    )

    statement = (
        select(Target, latest_check.c.last_started_at)
        .outerjoin(latest_check, latest_check.c.target_id == Target.id)
        .where(Target.enabled.is_(True))
        .order_by(Target.created_at)
    )

    due: list[Target] = []
    for target, last_started_at in db.execute(statement):
        if last_started_at is None:
            due.append(target)
            continue

        if last_started_at.tzinfo is None:
            last_started_at = last_started_at.replace(tzinfo=UTC)

        if last_started_at + timedelta(seconds=target.interval_seconds) <= current_time:
            due.append(target)

    return due
