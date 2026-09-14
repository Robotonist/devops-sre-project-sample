from uuid import UUID

from sqlalchemy import select
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
