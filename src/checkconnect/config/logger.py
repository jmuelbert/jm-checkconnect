# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""Cross-platform logger using structlog, JSON output, and TOML config."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

import structlog
import tomllib
from platformdirs import user_log_dir
from structlog.processors import (
    JSONRenderer,
    TimeStamper,
    add_log_level,
    format_exc_info,
)

from checkconnect.config.settings_manager import SettingsManager

APPNAME = "checkconnect"


class ConfiguredLogger:
    """Creates a configurable logger with file, rotating, and JSON support."""

    def __init__(self, config_file: Optional[Path] = None) -> None:
        """Initializes structlog with the loaded configuration."""
        config = SettingsManager()

        log_level = config.get("logger", "level", "INFO").upper()
        log_format = config.get(
            "logger",
            "format",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Structlog konfigurieren
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level, logging.INFO))
        )

        self._standard_logger = logging.getLogger(APPNAME)
        self.logger = structlog.get_logger()

        # Root logger setup
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        formatter = logging.Formatter(log_format)

        # Console handler with color support
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(console_handler)

        log_file_enabled = config.get("file_handler", "enabled", False)
        log_file_path = config.get("file_handler", "file_path", APPNAME + ".log")


        # If file logging is enabled
        if log_file_enabled:
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)

        log_rotating_enabled = config.get("limited_file_handler", "enabled", False)

        # If rotated logging is enabled
        if log_rotating_enabled:
            log_rotate_filepath = config.get("file_path", APPNAME + "_limited.log")
            if log_rotate_filepath is None:
                log_rotate_filepath = APPNAME + "_limited.log"  # Default value if None
            max_bytes = (
                config.get("max_bytes", 1024 * 1024) or 1024 * 1024
            )  # Default to 1MB
            backup_count = config.get("backup_count", 3) or 3  # Default to 3 backups
            rotating_handler = RotatingFileHandler(
                log_rotate_filepath,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            rotating_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(rotating_handler)

    def get_logger(self, name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
        """Return a named or default structlog logger."""
        return self.logger

    def info(self, msg: str) -> None:
        """Shortcut for info-level logging."""
        self.logger.info(msg)

    def exception(self, msg: str) -> None:
        """Shortcut for exception-level logging."""
        self.logger.exception(msg)
