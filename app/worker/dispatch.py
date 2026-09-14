from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories import list_due_targets


class QueueUnavailableError(RuntimeError):
    """Raised when a check cannot be submitted to the Celery broker."""


def enqueue_target_check(target_id: UUID) -> str:
    from kombu.exceptions import OperationalError as KombuOperationalError
    from redis.exceptions import RedisError

    from app.worker.tasks import run_target_check

    try:
        async_result = run_target_check.delay(str(target_id))
    except (KombuOperationalError, RedisError) as exc:
        raise QueueUnavailableError("check queue unavailable") from exc

    return str(async_result.id)


def check_redis() -> str:
    from redis import Redis
    from redis.exceptions import RedisError

    from app.core.config import get_settings

    client = Redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=1.0,
        socket_timeout=1.0,
    )
    try:
        client.ping()
    except RedisError:
        return "degraded"
    finally:
        client.close()

    return "ok"


def dispatch_due_targets_once(
    db: Session,
    *,
    enqueue: Callable[[UUID], str] = enqueue_target_check,
    now: datetime | None = None,
) -> int:
    due_targets = list_due_targets(db, now=now)
    for target in due_targets:
        enqueue(target.id)
    return len(due_targets)
