
import structlog
from structlog.processors import (
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    format_exc_info,
)
from structlog.stdlib import (
    add_log_level,
    add_logger_name,
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
