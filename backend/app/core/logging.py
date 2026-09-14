import logging
import sys
from app.core.config import settings


def setup_logging():
    log_format = "%(asctime)s [%(levelname)s] [request_id=%(request_id)s] %(name)s: %(message)s"
    
    # Custom filter to guarantee request_id is always present in log records
    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, "request_id"):
                record.request_id = "system"
            return True

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format))
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())
    root_logger.handlers = [handler]

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)


logger = logging.getLogger("flux_one")
