import logging
import sys
from pathlib import Path

import orjson
import sentry_sdk
import yarl
from loguru import logger

from settings.conf import settings

LOG_LEVEL = "INFO"

if settings.debug:
    LOG_LEVEL = "DEBUG"


TECHNICAL_ENDPOINTS = {}


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentaion.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record: logging.LogRecord):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def filter_transactions(event, hint):
    if "exc_info" in hint:
        return event

    if "request" in event:
        url_string = event["request"]["url"]
        parsed_url = yarl.URL(url_string)
        if parsed_url.path in TECHNICAL_ENDPOINTS:
            return None

    return event


def init_sentry():
    if sentry_dsn := settings.sentry_url:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.server_role,
            before_send_transaction=filter_transactions,
            send_default_pii=True,
            # TODO: Add sentry release
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for tracing.
            traces_sample_rate=1.0,
        )


# https://github.com/Delgan/loguru/issues/203#issuecomment-592183529
def sink_serializer(message):
    record = message.record

    exception = record["exception"]

    if exception is not None:
        exception = {
            "type": None if exception.type is None else exception.type.__name__,
            "value": exception.value,
            "traceback": bool(exception.traceback),
        }

    serializable = {
        "text": record["message"],
        "record": {
            "elapsed": {
                "repr": record["elapsed"],
                "seconds": record["elapsed"].total_seconds(),
            },
            "exception": exception,
            "extra": record["extra"],
            "file": {"name": record["file"].name, "path": record["file"].path},
            "function": record["function"],
            "level": {
                "icon": record["level"].icon,
                "name": record["level"].name,
                "no": record["level"].no,
            },
            "line": record["line"],
            "message": record["message"],
            "module": record["module"],
            "name": record["name"],
            "process": {"id": record["process"].id, "name": record["process"].name},
            "thread": {"id": record["thread"].id, "name": record["thread"].name},
            "time": {"repr": record["time"], "timestamp": record["time"].timestamp()},
        },
    }

    serialized = orjson.dumps(serializable, default=str).decode()
    print(serialized, file=sys.stdout)  # noqa: T201


def set_logging_config():
    # --- перенаправляем вывод sqlalchemy и uvicorn в loguru
    loggers = (
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict
        if name.startswith("uvicorn.") or name.startswith("sqlalchemy.")
    )

    intercept_handler = InterceptHandler()
    for replaced_logger in loggers:
        replaced_logger.handlers = []
    logging.getLogger("aiokafka").handlers = [intercept_handler]
    logging.getLogger("sqlalchemy").handlers = [intercept_handler]
    logging.getLogger("uvicorn").handlers = [intercept_handler]
    logging.getLogger("uvicorn.access").handlers = [intercept_handler]
    logging.getLogger("aio_pika").handlers = [intercept_handler]
    logging.getLogger("aiormq").handlers = [intercept_handler]
    logging.getLogger("aiohttp").handlers = [intercept_handler]
    logging.getLogger("httpcore").handlers = [intercept_handler]

    if settings.serialize_logs:
        fmt = "{message}"  # noqa: E501
        base_sink = sink_serializer
    else:
        fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"  # noqa: E501
        base_sink = sys.stdout

    handlers = [
        {
            "sink": base_sink,
            "format": fmt,
            "level": LOG_LEVEL,
            "enqueue": False,
            "serialize": False,
        }
    ]

    if settings.local_log_path and not settings.debug:
        log_path = Path(settings.local_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handlers.append(
            {
                "sink": log_path / "app.log",
                "format": fmt,
                "level": LOG_LEVEL,
                "rotation": "1 days",
                "retention": "14 days",
                "enqueue": True,
                "serialize": False,
            }
        )

    logger.configure(handlers=handlers)
