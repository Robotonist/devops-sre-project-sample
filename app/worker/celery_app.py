import logging
import os

from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.worker.schedule import BEAT_SCHEDULE

settings = get_settings()


@setup_logging.connect
def configure_celery_logging(loglevel: int | str | None = None, **_: object) -> None:
    configure_logging(
        os.getenv("SERVICE_NAME", "worker"),
        level=loglevel or logging.INFO,
    )


celery_app = Celery(
    "ops_appliance",
    broker=settings.redis_url,
    include=["app.worker.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    beat_schedule=BEAT_SCHEDULE,
)
