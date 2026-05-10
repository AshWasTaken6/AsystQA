import json
import logging
from datetime import UTC, datetime

from core.config import settings
from core.context import get_correlation_id


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": get_correlation_id(),
            "event": record.getMessage(),
        }

        context = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
            }
        }

        if context:
            payload["context"] = context

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())


configure_logging()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
