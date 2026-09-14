import json
import logging

from app.core.logging import JsonFormatter, configure_logging


def test_json_formatter_emits_service_context_without_secrets() -> None:
    record = logging.LogRecord(
        name="app.worker.tasks",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="target check completed",
        args=(),
        exc_info=None,
    )
    record.service = "worker"
    record.target_id = "target-123"
    record.task_id = "task-456"
    record.database_url = "postgresql://ops:super-secret@postgres/ops"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["service"] == "worker"
    assert payload["level"] == "INFO"
    assert payload["message"] == "target check completed"
    assert payload["target_id"] == "target-123"
    assert payload["task_id"] == "task-456"
    assert "database_url" not in payload
    assert "super-secret" not in json.dumps(payload)


def test_configure_logging_applies_default_service(capsys) -> None:
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    try:
        configure_logging("api")
        logging.getLogger("app.main").info("application ready")
        payload = json.loads(capsys.readouterr().out.strip())
    finally:
        root.handlers.clear()
        root.handlers.extend(old_handlers)
        root.setLevel(old_level)

    assert payload["service"] == "api"
    assert payload["level"] == "INFO"
    assert payload["message"] == "application ready"
