"""Central logging configuration for Platform-X.

Usage in modules:
    from app.core.logging_config import get_logger
    logger = get_logger(__name__)
    ...
    logger.warning("...", exc_info=True)

By default the root logger is configured once when the FastAPI app
starts (see app/main.py). Do not call basicConfig elsewhere.
"""

from __future__ import annotations

import logging
import os
import sys


_DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DEFAULT_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


_configured = False


def configure_logging() -> None:
    """Configure the root logger once for the whole process."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(_DEFAULT_LEVEL)

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
