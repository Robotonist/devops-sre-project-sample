from celery import Celery

from app.core.config import get_settings

settings = get_settings()

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
)
