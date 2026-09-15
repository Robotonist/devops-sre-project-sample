import json
import logging
import sys
from datetime import UTC, datetime

_CONTEXT_FIELDS = ("target_id", "task_id", "result_id", "error_type")


class JsonFormatter(logging.Formatter):
    def __init__(self, *, default_service: str = "app") -> None:
        super().__init__()
        self.default_service = default_service

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "service": getattr(record, "service", self.default_service),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for field in _CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = str(value)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(service: str, *, level: int | str = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(default_service=service))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.captureWarnings(True)
