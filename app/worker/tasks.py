import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.worker.celery_app import celery_app
from app.worker.dispatch import dispatch_due_targets_once
from app.worker.executor import execute_target_check

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.run_target_check")
def run_target_check(target_id: str) -> str | None:
    with Session(get_engine()) as db:
        result_id = execute_target_check(db, UUID(target_id))

    if result_id is None:
        logger.info("target no longer exists; skipping check", extra={"target_id": target_id})
        return None

    return str(result_id)


@celery_app.task(name="app.worker.tasks.dispatch_due_targets")
def dispatch_due_targets() -> int:
    with Session(get_engine()) as db:
        return dispatch_due_targets_once(db)
