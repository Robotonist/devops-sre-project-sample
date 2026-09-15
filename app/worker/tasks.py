import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.worker.celery_app import celery_app
from app.worker.dispatch import dispatch_due_targets_once
from app.worker.executor import execute_target_check

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.worker.tasks.run_target_check")
def run_target_check(task: object, target_id: str) -> str | None:
    task_id = getattr(getattr(task, "request", None), "id", None)
    context = {"target_id": target_id, "task_id": task_id}
    logger.info("target check started", extra=context)

    with Session(get_engine()) as db:
        result_id = execute_target_check(db, UUID(target_id))

    if result_id is None:
        logger.info("target no longer exists; skipping check", extra=context)
        return None

    logger.info(
        "target check completed",
        extra={**context, "result_id": str(result_id)},
    )
    return str(result_id)


@celery_app.task(name="app.worker.tasks.dispatch_due_targets")
def dispatch_due_targets() -> int:
    with Session(get_engine()) as db:
        return dispatch_due_targets_once(db)
