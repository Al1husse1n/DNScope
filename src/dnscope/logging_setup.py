import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from dnscope.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure root logger with JSON formatter at settings.log_level.

    Every record includes at minimum: timestamp, level, logger, message.
    HTTP request logs include request_id, method, path, status, duration_ms.
    Do NOT configure uvicorn's access logger to double-log — set it to
    propagate=False and use our middleware instead.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Disable uvicorn.access double-logging
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.propagate = False
    uvicorn_access.handlers = []
