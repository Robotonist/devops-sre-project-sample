from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import create_target, get_target, list_check_results, list_targets
from app.db.session import get_db
from app.schemas.check_result import CheckResultRead
from app.schemas.target import TargetCreate, TargetRead
from app.worker.dispatch import QueueUnavailableError, enqueue_target_check

router = APIRouter(prefix="/api/v1/targets", tags=["targets"])


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
def create_target_route(payload: TargetCreate, db: Session = Depends(get_db)) -> TargetRead:
    try:
        return create_target(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A target with that name already exists",
        ) from exc


@router.get("", response_model=list[TargetRead])
def list_targets_route(db: Session = Depends(get_db)) -> list[TargetRead]:
    return list_targets(db)


@router.get("/{target_id}", response_model=TargetRead)
def get_target_route(target_id: UUID, db: Session = Depends(get_db)) -> TargetRead:
    target = get_target(db, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return target


@router.get("/{target_id}/checks", response_model=list[CheckResultRead])
def list_check_results_route(
    target_id: UUID, db: Session = Depends(get_db)
) -> list[CheckResultRead]:
    if get_target(db, target_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return list_check_results(db, target_id)


@router.post("/{target_id}/check", status_code=status.HTTP_202_ACCEPTED)
def run_target_check_route(target_id: UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    if get_target(db, target_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    try:
        task_id = enqueue_target_check(target_id)
    except QueueUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Check queue unavailable",
        ) from exc

    return {"task_id": task_id}
