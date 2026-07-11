import logging
import sys
from pythonjsonlogger import jsonlogger
from src.config import settings


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("multi-agent-platform")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.handlers.clear()
    logger.addHandler(handler)

    return logger


logger = setup_logger()
