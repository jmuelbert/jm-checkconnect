# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
A comprehensive logging manager for cross-platform logging with support for structured logging, file rotation, and JSON output.

The `LoggingManager` class is responsible for setting up and managing logging in the application. It integrates Python's built-in logging system with `structlog` to enable structured logging. The logging system supports logging to both the console (with color formatting) and log files, including automatic log file rotation.

Features:
--------
- Console logging with colorized output.
- File-based logging with automatic rotation based on size.
- Support for JSON-formatted log output (using `structlog`).
- Configuration via a TOML file, enabling flexible and customizable logging settings.
- Context manager support for clean logging setup and teardown.
- Easy integration into the application with a simple API for logging messages.

The class can be configured through a TOML configuration file (`config.toml`) that allows the user to specify:
- Log level (e.g., `INFO`, `DEBUG`, `ERROR`).
- Log format for console and file logging.
- Whether to enable log file rotation.
- Location of log files and rotation settings.

Example usage:
--------------
Here is an example of how to use the `LoggingManager` in your application:

    with LoggingManager(config_file='path/to/config.toml') as logger:
        # Get a structured logger for your app
        log = logger.get_logger()

        # Log an info message with additional data
        log.info("Application started", user="admin", environment="production")

        # Log an error message with exception information
        try:
            1 / 0  # Simulating an error
        except ZeroDivisionError as e:
            log.exception("An error occurred", exception=str(e))

The `LoggingManager` is designed to be used as a context manager, ensuring that resources are properly cleaned up (such as closing file handlers) when done.

Attributes
----------
- config (dict[str, Any]): Application configuration settings.
- log_dir (Path): The directory where log files are saved.
- _structlog_configured (bool): Internal flag to track if structlog has been configured.

Methods
-------
- __enter__(self): Start a context for the logger.
- __exit__(self, exc_type, exc_val, exc_tb): Clean up logging resources when exiting the context.
- get_logger(name: str | None = None) -> BoundLogger: Get a configured `structlog` logger instance.
- info(msg: str, **kwargs: Any) -> None: Log an info-level message.
- exception(msg: str, **kwargs: Any) -> None: Log an exception with traceback.
- error(msg: str, **kwargs: Any) -> None: Log an error-level message.
- warning(msg: str, **kwargs: Any) -> None: Log a warning-level message.
- debug(msg: str, **kwargs: Any) -> None: Log a debug-level message.

Exceptions Raised:
-----------------
- ConfigFileNotFoundError: Raised if the specified configuration file is not found.
- InvalidConfigFileError: Raised if the configuration file is invalid or cannot be parsed.
- InvalidLogLevelError: Raised if an invalid log level is provided in the configuration.
- LogDirectoryError: Raised if the log directory cannot be created.
- LogHandlerError: Raised if a logging handler cannot be created for the file or console output.

Usage of this class enables better control over application logging, helping with both development and production diagnostics. The logging system is designed to be flexible, powerful, and easy to use while maintaining high configurability.

"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Self, Unpack

import structlog
from platformdirs import user_log_dir

from checkconnect.__about__ import __app_name__
from checkconnect.config.settings_manager import (
    SettingsManager,
    SettingsManagerSingleton,
)
from checkconnect.config.translation_manager import get_translator

if TYPE_CHECKING:
    from types import TracebackType

    from structlog.stdlib import BoundLogger
    from structlog.typing import Processor


# --- Custom Exceptions ---
class LoggerConfigurationError(Exception):
    """Base exception for logger configuration errors."""


class InvalidLogLevelError(LoggerConfigurationError, ValueError):
    """Raised when an invalid log level string is found in the config."""


class LogDirectoryError(LoggerConfigurationError, OSError):
    """Raised when creating the log directory fails."""


class LogHandlerError(LoggerConfigurationError, OSError):
    """Raised when creating a log file handler fails."""


# Shared structlog processors with proper typing
SHARED_PROCESSORS: Final[list[Processor]] = [
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True), # UTC is good for logs
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    # No renderers here! Renderers should be part of the formatter setup.
]

# --- Logging Manager ---
class LoggingManager:
    """
    A logging manager for cross-platform logging with structured.

    This class provides a centralized way to configure and manage logging
    in your application. It integrates Python's logging system with structlog
    to support both structured logging and standard console/file-based logging
    with log rotation.

    Features:
    - Console logging with colored output.
    - File logging with automatic rotation.
    - JSON logging via structlog for structured logs.
    - Configurable via a TOML file, allowing flexible log settings.
    - Context manager support for automatic resource cleanup.

    The configuration file allows specifying:
    - Log level (e.g., `INFO`, `DEBUG`, `ERROR`).
    - Log format for both console and file outputs.
    - Log file rotation settings (e.g., max size, backup count).
    - Log file locations.

    Example usage:
    --------------
    with LoggingManager(config_file="path/to/config.toml") as logger:
        log = logger.get_logger()
        log.info("Application started", user="admin", env="production")

    Attributes
    ----------
    config SettingsManager: Application configuration settings.
    log_dir : Path
        Directory where log files are stored.
    _structlog_configured : bool
        Internal flag to track structlog configuration status.

    Methods
    -------
    __enter__() -> LoggingManager
        Enter the context and return the logging manager instance.
    __exit__(exc_type, exc_val, exc_tb) -> None
        Clean up resources on exiting the context.
    get_logger(name: Optional[str] = None) -> BoundLogger
        Retrieve a structured logger instance.
    info(msg: str, **kwargs: Any) -> None
        Log an info message.
    exception(msg: str, **kwargs: Any) -> None
        Log an exception message with traceback.
    error(msg: str, **kwargs: Any) -> None
        Log an error message.
    warning(msg: str, **kwargs: Any) -> None
        Log a warning message.
    debug(msg: str, **kwargs: Any) -> None
        Log a debug message.

    Exceptions Raised:
    -----------------
    InvalidLogLevelError
        Raised if an invalid log level is provided in the config.
    LogDirectoryError
        Raised if the log directory cannot be created.
    LogHandlerError
        Raised if a log handler cannot be created.

    This class provides a flexible and robust logging setup, ensuring your
    application can handle logging requirements for both development and production.

    """

    # Constants with improved typing
    APP_NAME: Final[str] = __app_name__
    DEFAULT_LOG_FILENAME: Final[str] = APP_NAME + ".log"
    DEFAULT_LIMITED_LOG_FILENAME: Final[str] = "limited_" + APP_NAME + ".log"
    DEFAULT_MAX_BYTE: Final[int] = 1024 * 1024
    DEFAULT_BACKUP_COUNT: Final[int] = 3

    def __init__(
        self,
        config: SettingsManager | None = None,
        cli_log_level: int | None = None
    ) -> None:
        """
        Initialize logger.

        Args:
            config: An optional SettingsManager instance.
            cli_log_level: Optional. A logging module level (e.g., logging.DEBUG, logging.INFO)
                           to override the level read from the config file.
        """
        self.config = config or SettingsManagerSingleton.get_instance()
        self.log_dir = self._ensure_log_dir() # Can raise LogDirectoryError
        self._active_handlers = []
        self._ = get_translator().gettext

        # Call the public setup method
        self.setup_logging(cli_log_level) # Can raise specific exceptions

    def __enter__(self) -> Self:
        """Enter the context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exit the context manager and clean up resources.

        This method ensures proper cleanup of logging resources by:
        1. Shutting down all logging handlers
        2. Resetting structlog to its default state
        """
        self.shutdown()

    def _ensure_log_dir(self) -> Path:
        """
        Ensure the log directory exists and return its path.

        Returns
        -------
            The path to the log directory.

        Raises
        ------
            LogDirectoryError: If creating the log directory fails.

        """
        log_dir = Path(user_log_dir(self.APP_NAME))
        try:
            log_dir.mkdir(parents=True, exist_ok=True)

        except OSError as e:
            msg = self._(f"Failed to create log directory {log_dir}: {e}")
            raise LogDirectoryError(msg) from e
        else:
            return log_dir

    def _resolve_log_path(self, filename: str) -> Path:
        """
        Return full path to the log file in the OS-specific log directory.

        Args:
        ----
            filename: The name of the log file.

        Returns:
        -------
            A Path object representing the full path to the log file.

        """
        return self.log_dir / filename

    def setup_logging(
        self,
        cli_override_level: int | None = None
    ) -> structlog.stdlib.BoundLogger:
        """
        Configures structlog and Python logging handlers. This method can be called
        publicly to reconfigure logging if necessary, e.g., to change the log level.

        Args:
            cli_override_level: An optional logging module level (e.g., logging.DEBUG)
                                that overrides the level from the config file.

        Returns
        -------
            A structlog logger instance configured according to the loaded
            configuration.

        Raises
        ------
            InvalidLogLevelError: If the config contains an invalid log level.
            LogHandlerError: If creating log file handlers fails.

        """
        logger_config = self.config.get_section("logger")
        log_level_str = logger_config.get("level", "INFO").upper()

        # Determine the final log level: CLI override takes precedence
        if cli_override_level is not None:
            log_level = cli_override_level
        else:
            # Validate log level from config
            log_level = getattr(logging, log_level_str, None)
            if log_level is None:
                msg = self._(f"Invalid log level specified: {log_level_str}")
                raise InvalidLogLevelError(msg)

        # Configure root logger
        root_logger = logging.getLogger()

        # Remove existing handlers to prevent duplicates, especially important for re-configuration
        # or in testing environments where the logger might be setup multiple times.
        # This loop iterates over a copy of the handlers list because removing items
        # while iterating the original can lead to unexpected behavior.
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        self._active_handlers.clear() # Also clear the internal tracking list

        root_logger.setLevel(log_level) # Set the root logger's level

        # Create formatters for standard logging handlers using structlog's ProcessorFormatter
        # The `log_format` from your config.toml won't directly be used by logging.Formatter here.
        # Instead, ProcessorFormatter renders the structlog event dictionary.
        # You would pass a format string as an argument to the renderer (e.g., ConsoleRenderer)
        # if the renderer supports it for custom text output.
        console_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
                # Consider if you can pass `log_format` here as an argument to ConsoleRenderer
                # if it allows customization to achieve your desired format.
                # Many structlog renderers ignore the standard `logging.Formatter`'s format string;
                # you control ConsoleRenderer's output through its own options.
            ),
            foreign_pre_chain=SHARED_PROCESSORS,
        )

        file_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(), # JSON for file logging is a good choice
            foreign_pre_chain=SHARED_PROCESSORS,
        )

        # Add handlers (now using the `ProcessorFormatter` instances)
        try:
            self._add_console_handler(console_formatter, root_logger)
        except LogHandlerError as e:
            print(self._(f"CRITICAL ERROR: Failed to add console handler: {e}"), file=sys.stderr)
            raise

        try:
            self._add_file_handlers(file_formatter, root_logger) # Can raise LogHandlerError
        except LogHandlerError as e:
            print(self._(f"WARNING: Failed to add file handlers: {e}"), file=sys.stderr)

        # Configure structlog itself (only if not already configured).
        # `structlog.is_configured()` checks if structlog.configure() has been called successfully.
        if not structlog.is_configured():
            structlog.configure(
                processors=[
                    *SHARED_PROCESSORS,
                    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
                ],
                wrapper_class=structlog.make_filtering_bound_logger(log_level),
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True, # Recommended for performance
            )
        else:
            # If already configured (e.g., in tests), structlog.configure() might not
            # re-apply all settings if `cache_logger_on_first_use` is True for existing loggers.
            # However, for a one-time CLI setup, this path is usually less critical.
            # You might log a warning here if this scenario is unexpected.
            pass

        return structlog.get_logger(self.APP_NAME)

    def _add_console_handler(
        self,
        formatter: structlog.stdlib.ProcessorFormatter,
        root_logger: logging.Logger,
    ) -> None:
        """
        Add a console handler to the root logger.

        Args:
        ----
            formatter: The formatter to use for log messages
            root_logger: The root logger to add the handler to

        Raises:
        ------
            LogHandlerError: If the console handler creation fails

        """
        try:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            self._active_handlers.append(console_handler)
        except TypeError as te:
            msg = self._(f"Formatter not valid or missing format method: {te}")
            raise LogHandlerError(msg) from te
        except AttributeError as ae:
            msg = self._(f"Formatter is None or object has no formatter: {ae}")
            raise LogHandlerError(msg) from ae
        except MemoryError as me:
            msg = self._(f"System had not enough memory: {me}")
            raise LogHandlerError(msg) from me
        except Exception as e: # Catch potential errors during handler setup
            msg = self._(f"Failed to add console handler: {e}")
            raise LogHandlerError(msg) from e

    def _add_file_handlers(
        self,
        formatter: structlog.stdlib.ProcessorFormatter,
        root_logger: logging.Logger,
    ) -> None:
        """
        Add file and rotating file handlers to the root logger.

        Raises
        ------
            LogHandlerError: If creating log file handlers fails.

        """
        file_handler_config = self.config.get_section("file_handler")
        if file_handler_config.get("enabled", False):
            file_name = file_handler_config.get(
                "file_path",
                self.DEFAULT_LOG_FILENAME,
            )
            file_path = self._resolve_log_path(file_name)
            try:
                file_handler = logging.FileHandler(file_path)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                self._active_handlers.append(file_handler)
            except (OSError, ValueError) as e:
                msg = self._(
                    f"Failed to create file handler for {file_path}: {e}",
                )
                raise LogHandlerError(msg) from e

        # Rotating file handler
        rotating_handler_config = self.config.get_section("limited_file_handler")
        if rotating_handler_config.get("enabled", False):
            file_name = rotating_handler_config.get(
                "file_path",
                self.DEFAULT_LIMITED_LOG_FILENAME,
            )
            file_path = self._resolve_log_path(file_name)
            try:
                max_bytes = int(rotating_handler_config.get("max_bytes", 1024))
                backup_count = int(rotating_handler_config.get("backup_count", 5))
                rotating_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                )
                rotating_handler.setFormatter(formatter)
                root_logger.addHandler(rotating_handler)
                self._active_handlers.append(rotating_handler)
            except (OSError, ValueError) as e:
                msg: str = self._(
                    f"Failed to create rotating file handler for {file_path}: {e} ",
                )
                raise LogHandlerError(msg) from e

    def shutdown(self) -> None:
        """
        Closes and removes all active handlers and resets structlog.

        This method iterates through the handlers added by this manager,
        closes them, and removes them from the root logger. It then
        resets the structlog configuration and disables logging.
        """
        root_logger = logging.getLogger()

        # Close and remove only handlers explicitly managed by this LoggingManager.
        # Iterate over a copy of the list of handlers to safely remove items.
        for hdlr in root_logger.handlers[:]:
            if hdlr in self._active_handlers: # Check if it's one of ours
                hdlr.close()
                root_logger.removeHandler(hdlr)
        self._active_handlers.clear() # Clear the internal tracking list

        # Call logging.shutdown() to flush buffers and perform final cleanup on all loggers.
        # This is generally a good practice at application exit.
        logging.shutdown()
        # Reset structlog to its default unconfigured state.
        structlog.reset_defaults()
        # Optionally, reset the root logger level and disable state.
        # logging.shutdown() usually sets the root logger level to NOTSET,
        # but explicitly setting it and disabling ensures a clean state.
        root_logger.setLevel(logging.NOTSET)
        logging.disable(logging.NOTSET)

    def get_logger(self, name: str | None = None) -> BoundLogger:
        """
        Get a logger instance.

        Args:
        ----
            name: The name of the logger. If None, uses APP_NAME.

        Returns:
        -------
            A configured structlog logger instance.

        Note:
        ----
            Configuration is cached after the first call to avoid
            unnecessary reconfiguration of structlog.

        """

        return structlog.get_logger(name if name is not None else self.APP_NAME)

    def info(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for info-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        # Ensure _logger is initialized; for a robust manager, this should be safe.
        # In this setup, _setup_logger is called in __init__, so _logger will exist.
        # If get_logger is called directly before any logging, it ensures the logger is bound.
        structlog.get_logger(self.APP_NAME).info(msg, **kwargs)

    def exception(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for exception-level logging, automatically adding exc_info.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).exception(msg, **kwargs) # structlog's exception handles exc_info

    def error(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for error-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).error(msg, **kwargs)

    def warning(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for warning-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).warning(msg, **kwargs)

    def debug(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for debug-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).debug(msg, **kwargs)


class LoggingManagerSingleton:
    _instance: LoggingManager | None = None

    @classmethod
    def get_instance(cls, cli_log_level: int | None = None) -> LoggingManager:
        if cls._instance is None:
            # Pass cli_log_level when creating the instance the first time
            cls._instance = LoggingManager(cli_log_level=cli_log_level)
        # If an instance already exists, you might want to re-configure its level
        # if a different cli_log_level is provided. However, for typical CLIs,
        # the singleton is instantiated once at the start with the correct level.
        # If you truly need to change the level of an *already existing* singleton
        # instance, you would call `cls._instance.setup_logging(cli_log_level)`.
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        if cls._instance:
            cls._instance.shutdown() # Ensure handlers are closed on reset
        cls._instance = None
