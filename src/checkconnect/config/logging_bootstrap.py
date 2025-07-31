import logging
import sys

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import (
    TimeStamper,
    StackInfoRenderer,
    format_exc_info,
    UnicodeDecoder,
)
from structlog.stdlib import (
    add_logger_name,
    add_log_level,
    LoggerFactory,
    BoundLogger,
    ProcessorFormatter,
)


def bootstrap_logging() -> None:
    """
    Configure a minimal structlog setup that can be used immediately
    before the full application configuration is loaded.
    """
    if structlog.is_configured():
        return

    # --- Define processors used by structlog ---
    base_processors = [
        add_logger_name,
        add_log_level,
        TimeStamper(fmt="iso", utc=True),
        StackInfoRenderer(),
        format_exc_info,
        UnicodeDecoder(),
    ]

    # --- Configure structlog ---
