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
- InvalidLogLevelError: Raised if an invalid log level is provided in the configuration.
- LogDirectoryError: Raised if the log directory cannot be created.
- LogHandlerError: Raised if a logging handler cannot be created for the file or console output.

Usage of this class enables better control over application logging, helping with both development and production diagnostics. The logging system is designed to be flexible, powerful, and easy to use while maintaining high configurability.

"""

from __future__ import annotations

import traceback
import logging
import logging.config
import logging.handlers
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any, ClassVar, Final, Self, Unpack

import structlog
from rich.console import Console
from structlog.stdlib import ProcessorFormatter

from checkconnect.__about__ import __app_name__
from checkconnect.config.appcontext import AppContext
from checkconnect.config.settings_manager import SettingsManager
from checkconnect.config.translation_manager import TranslationManagerSingleton
from checkconnect.exceptions import LogHandlerError

if TYPE_CHECKING:
    from types import TracebackType

    from structlog.stdlib import BoundLogger
    from structlog.typing import Processor


# Define a placeholder for the manager's logger until it's configured
# This is typically done with a basicConfig or by configuring root logger early.
# For demo, let's assume `logging` is available.
# This ensures that even before the LoggingManager is fully set up,
# basic logging messages can be emitted.
logging.basicConfig(level=logging.INFO)  # Bootstrap basic logging

error_console = Console(file=sys.stderr)

VERBOSITY_LEVELS = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}


# --- Logging Manager ---
class LoggingManager:
    """
    A logging manager for cross-platform logging with structured.

    Manages the full configuration of the application's logging.
    This class is responsible for setting up various log handlers
    (console, file, rotating file) based on provided settings.

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

    _logger: structlog.stdlib.BoundLogger
    _internal_errors: list[str]
    effective_log_level: int

    # Constants with improved typing
    APP_NAME: Final[str] = __app_name__
    DEFAULT_LOG_FILENAME: Final[str] = APP_NAME + ".log"
    DEFAULT_LIMITED_LOG_FILENAME: Final[str] = "limited_" + APP_NAME + ".log"
    DEFAULT_MAX_BYTE: Final[int] = 1024 * 1024
    DEFAULT_BACKUP_COUNT: Final[int] = 3

    # Setzen Sie den Typ für '_' hier
    # Es ist eine Funktion, die einen String nimmt und einen String zurückgibt.
    _: Callable[[str], str]

    def __init__(self) -> None:
        """
        Initialize LoggingManager attributes with default/None values.

        Does NOT apply the full logging configuration yet.
        Call .apply_configuration() to set up logging.
        """
        print("[DEBUG] LoggingManager instance created (lightweight init)")

        self._internal_errors = []
        self._logger = None

        # Attributes that will be set by apply_configuration
        self.cli_log_level: int | None = None
        self.enable_console_logging: bool = False
        self.log_config: dict[str, Any] = {}
        self.effective_log_level = 0
        self.translator: Any = None  # Or use a dummy translator if needed immediately
        self._ = lambda x: x

    def apply_configuration(
        self,
        *,
        cli_log_level: int | None = None,
        enable_console_logging: bool,
        log_config: dict[str, Any],
        translator: Any,
    ) -> None:
        """
        Apply the full logging configuration to the manager.

        This method should be called by the Singleton manager.
        """
        print("[DEBUG] LoggingManager.apply_configuration called.")

        # Clear previous errors for a fresh configuration attempt
        self._internal_errors.clear()

        # Set instance attributes
        self.cli_log_level = cli_log_level
        self.enable_console_logging = enable_console_logging
        self.log_config = log_config
        self.translator = translator
        self._ = self.translator.translate  # Convenient alias for translation

        # Use a temporary logger for messages *during* configuration,
        # before the full structlog setup is complete.
        temp_logger = structlog.get_logger("LoggingManagerInit")
        temp_logger.debug(self._("LoggingManager instance created. Applying configuration..."))

        try:
            # All the logic that was previously in your original __init__ goes here
            # (e.g., setting up structlog, configuring handlers, etc.)
            self._apply_full_configuration()  # This method would contain your actual logging setup logic

            temp_logger.info(self._("Full logging configuration applied."))
        except Exception as e:  # Catch specific LogHandlerError if possible
            print(traceback.format_exc())  # TEMPORARY
            error_msg = self._("Critical error applying logging configuration: ")
            self._internal_errors.append(error_msg + str(e))
            temp_logger.exception(error_msg)
            # Re-raise for the singleton to catch and report as critical
            raise

    def shutdown(self) -> None:
        """
        Shut down logging handlers to ensure logs are flushed and resources released.

        This should be called during application exit, especially in tests.
        """
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)

    def get_logger(self, name: str | None = None) -> structlog.stdlib.BoundLogger:
        """Return the main application logger instance."""
        return structlog.get_logger(name) if name else structlog.get_logger()

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

    def debug(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for debug-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).debug(msg, **kwargs)

    def warning(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for warning-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).warning(msg, **kwargs)

    def error(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for error-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).error(msg, **kwargs)

    def critical(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for error-level logging.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).error(msg, **kwargs)

    def exception(self, msg: str, **kwargs: Unpack[dict[str, Any]]) -> None:
        """
        Shortcut for exception-level logging, automatically adding exc_info.

        Args:
        ----
            msg: The message to log.
            **kwargs: Additional key-value pairs to include in the log record.

        """
        structlog.get_logger(self.APP_NAME).exception(msg, **kwargs)  # structlog's exception handles exc_info

    def get_instance_errors(self) -> list[str]:
        """Exposes internal errors encountered during configuration."""
        return list(self._internal_errors)

    # --- private methods ---
    def _clear_existing_handlers(self, root_logger: logging.Logger) -> None:
        """Clear all existing handlers from the root logger."""
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        self._logger.debug(self._("Cleared existing root logger handlers."))

    def _get_effective_log_level(self, logger_main_settings: dict[str, Any]) -> int:
        """Determine the effective log level based on settings and CLI override."""
        # 1. Get level from settings (config.toml)
        settings_level_str = logger_main_settings.get("level", "INFO").upper()
        effective_level = getattr(logging, settings_level_str, None)
        self._logger.debug(
            self._("Effective log level from settings: "),
            settings_level_str=settings_level_str,
            effective_level=effective_level,
        )

        # Handle invalid settings level
        if not isinstance(effective_level, int):
            self._internal_errors.append(
                self._(f"Invalid log level '{settings_level_str}' in config. Falling back to INFO.")
            )
            effective_level = logging.INFO
            self._logger.warning(
                self._("Invalid log level from settings. Falling back to INFO."), settings_level_str=settings_level_str
            )
        else:
            self._logger.debug(self._("Config log level is valid."), config_level=logging.getLevelName(effective_level))

        # 2. Apply CLI log level override
        # The 'min' function here is crucial: a lower numerical value means higher verbosity.
        # So, min(WARNING, INFO) = WARNING. min(INFO, DEBUG) = INFO.
        # This implies that if CLI is more verbose (e.g., DEBUG), it will be a lower number than config (e.g., INFO).
        # Your description "CLI log level applied, potentially increasing verbosity" confirms this.
        # For example: if config is INFO (20) and CLI is DEBUG (10), min(20, 10) = 10 (DEBUG).
        # If config is DEBUG (10) and CLI is WARNING (30), min(10, 30) = 10 (DEBUG).
        # This correctly means CLI only "increases" verbosity (makes the level number smaller)
        # if the CLI level itself is more verbose than the config.
        if self.cli_log_level is not None:
            # We assume self.cli_log_level is already a valid logging int level from VERBOSITY_LEVELS
            original_effective_level = effective_level
            effective_level = min(effective_level, self.cli_log_level)
            self._logger.info(
                self._("CLI log level applied, potentially increasing verbosity."),
                cli_log_level=logging.getLevelName(self.cli_log_level),
                original_effective_level=logging.getLevelName(original_effective_level),
                final_effective_level=logging.getLevelName(effective_level),
            )
        else:
            self._logger.debug(self._("No CLI log level provided, using config/default."))

        self._logger.debug(
            self._("Final effective log level calculated."), final_level=logging.getLevelName(effective_level)
        )
        return effective_level

    def _get_primary_renderer(self, logger_main_settings: dict[str, Any]) -> Any:
        """Determineand returns the primary structlog renderer."""
        output_format = logger_main_settings.get("output_format", "console").lower()
        if output_format == "json":
            self._logger.debug(self._("Using JSONRenderer for output."))
            return structlog.processors.JSONRenderer()
        else:
            self._logger.debug(self._("Using ConsoleRenderer for output."))
            return structlog.dev.ConsoleRenderer()

    def _get_shared_processors(self) -> list[Any]:
        """Return the list of shared structlog processors."""
        self._logger.debug(self._("Defining shared structlog processors."))
        return [
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

    def _setup_console_handler(
        self,
        root_logger: logging.Logger,
        primary_renderer: Any,
        shared_processors: list[Any],
        console_handler_settings: dict[str, Any],
    ) -> None:
        """Set up the console log handler if enabled."""
        if self.enable_console_logging or console_handler_settings.get("enabled"):
            try:
                console_handler = logging.StreamHandler(sys.stdout)
                console_formatter = ProcessorFormatter(
                    processor=primary_renderer,
                    foreign_pre_chain=shared_processors,
                )
                console_handler.setFormatter(console_formatter)
                root_logger.addHandler(console_handler)
                self._logger.debug(self._("Console handler added."))
            except Exception as e:
                msg = self._("Failed to set up console handler:")
                self._internal_errors.append(msg + str(e))
                self._logger.exception(msg)

    def _setup_file_handler(
        self,
        root_logger: logging.Logger,
        primary_renderer: Any,
        shared_processors: list[Any],
        file_handler_settings: dict[str, Any],
        logger_main_settings: dict[str, Any],
    ) -> None:
        """Set up the main file log handler if enabled."""
        if file_handler_settings.get("enabled"):
            try:
                file_name = file_handler_settings.get("file_name", "checkconnect.log")
                log_dir_str = logger_main_settings.get("log_directory")
                if not log_dir_str:
                    msg = self._("Log directory not specified in settings for file handler.")
                    raise ValueError(mesg)
                log_dir = Path(log_dir_str)
                log_file_path = log_dir / file_name
                log_file_path.parent.mkdir(parents=True, exist_ok=True)

                file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
                file_formatter = ProcessorFormatter(
                    processor=primary_renderer,
                    foreign_pre_chain=shared_processors,
                )
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)
                self._logger.debug(self._(f"File handler added {log_file_path}"))
            except Exception as e:
                msg = self._("Failed to set up file handler: ")
                self._internal_errors.append(msg + str(e))
                self._logger.exception(msg)

    def _setup_limited_file_handler(
        self,
        root_logger: logging.Logger,
        primary_renderer: Any,
        shared_processors: list[Any],
        limited_file_handler_settings: dict[str, Any],
        logger_main_settings: dict[str, Any],
    ) -> None:
        """Set up the rotating file log handler if enabled."""
        if limited_file_handler_settings.get("enabled"):
            try:
                file_name = limited_file_handler_settings.get("file_name", "limited_checkconnect.log")
                max_bytes = limited_file_handler_settings.get("max_bytes", 1024 * 1024 * 5)  # Default 5MB
                backup_count = limited_file_handler_settings.get("backup_count", 5)

                log_dir_str = logger_main_settings.get("log_directory")
                if not log_dir_str:
                    msg = self._("Log directory not specified in settings for limited file handler.")
                    raise ValueError(msg)
                log_dir = Path(log_dir_str)
                limited_log_file_path = log_dir / file_name
                limited_log_file_path.parent.mkdir(parents=True, exist_ok=True)

                rotating_handler = logging.handlers.RotatingFileHandler(
                    limited_log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
                )
                rotating_formatter = ProcessorFormatter(
                    processor=primary_renderer,
                    foreign_pre_chain=shared_processors,
                )
                rotating_handler.setFormatter(rotating_formatter)
                root_logger.addHandler(rotating_handler)
                self._logger.debug(self._(f"Limited file handler added. {limited_log_file_path}"))
            except Exception as e:
                msg = self._("Failed to set up limited file handler: ")
                self._internal_errors.append(msg + str(e))
                self._logger.exception(msg)

    # The main _apply_full_configuration method, now much shorter
    def _apply_full_configuration(self) -> None:
        """Apply the full structlog and standard logging configuration."""
        print("[DEBUG] _apply_configuration was called")
        if self._logger is None:
            # Use a simple structlog logger for setup messages
            self._logger = structlog.get_logger("LoggingManagerInit")
            self._logger.debug("LoggingManagerInit logger assigned for setup messages.")

        root_logger = logging.getLogger()
        self._clear_existing_handlers(root_logger)

        if not self.log_config:
            self._internal_errors.append("Logging configuration dictionary is empty.")
            self._logger.warning("No logging configuration provided.")

        logger_main_settings = self.log_config.get("logger", {})
        console_handler_settings = self.log_config.get("console_handler", {})
        file_handler_settings = self.log_config.get("file_handler", {})
        limited_file_handler_settings = self.log_config.get("limited_file_handler", {})

        self.effective_log_level = self._get_effective_log_level(logger_main_settings)
        root_logger.setLevel(self.effective_log_level)
        self._logger.debug(self._("Root logger level set level"), effective_level=self.effective_log_level)

        primary_renderer = self._get_primary_renderer(logger_main_settings)
        shared_processors = self._get_shared_processors()

        self._setup_console_handler(root_logger, primary_renderer, shared_processors, console_handler_settings)
        self._setup_file_handler(
            root_logger, primary_renderer, shared_processors, file_handler_settings, logger_main_settings
        )
        self._setup_limited_file_handler(
            root_logger, primary_renderer, shared_processors, limited_file_handler_settings, logger_main_settings
        )

        # ✅ Re-fetch the logger AFTER configuration
        self._logger = structlog.get_logger("LoggingManagerInit")

        self._logger.debug(self._("Structlog core configured."))


class LoggingManagerSingleton:
    """
    Singleton class for LoggingManager.

    Ensures a single instance manages application logging
    and handles its controlled initialization.
    """

    _instance: LoggingManager | None = None
    _initialization_errors: ClassVar[list[str]] = []
    _is_configured: ClassVar[bool] = False  # Track if the instance has been configured

    @classmethod
    def get_instance(cls) -> LoggingManager:
        """
        Return the single instance of LoggingManager.

        Raises RuntimeError if not yet initialized.
        """
        if cls._instance is None:
            raise RuntimeError("LoggingManager has not been initialized. Call initialize_from_context first.")
        return cls._instance

    @classmethod
    def initialize_from_context(
        cls, *, app_context: AppContext, cli_log_level: int | None = None, enable_console_logging: bool = True
    ) -> None:
        """
        Initialize the LoggingManagerSingleton.

        Using settings from the AppContext
        and CLI-derived parameters.
        """
        print("[DEBUG] initialize_from_context was called")
        print("[DEBUG] initialize_from_context was called. cls._is_configured: ", cls._is_configured)
        if cls._is_configured:
            # Use the already configured logger if available, otherwise bootstrap
            current_logger = cls._instance.get_logger() if cls._instance else logging.getLogger(__name__)
            current_logger.warning("Attempted to re-initialize LoggingManagerSingleton, but it's already configured.")
            cls._initialization_errors.append("LoggingManagerSingleton already configured. Cannot re-configure.")
            return  # Prevent re-initialization

        # Create the lightweight instance if it doesn't exist yet
        print("[DEBUG] initialize_from_context was called. cls._instance: ", cls._instance)
        if cls._instance is None:
            try:
                cls._instance = LoggingManager()  # Lightweight creation
            except Exception as e:
                cls._initialization_errors.append(f"Error creating LoggingManager instance: {e}")
                cls._instance = None
                raise  # Re-raise critical creation error

        cls._initialization_errors.clear()  # Clear errors for a fresh initialization attempt

        try:
            print("[DEBUG by INIT] configure_logging from context: ", app_context.settings)
            print("[DEBUG by INIT] configure_logging from context: ", app_context.settings.get_section("logger"))
            print(
                "[DEBUG by INIT] configure_logging from context: ", app_context.settings.get_section("console_handler")
            )
            print("[DEBUG by INIT] configure_logging from context: ", app_context.settings.get_section("file_handler"))
            print(
                "[DEBUG by INIT] configure_logging from context: ",
                app_context.settings.get_section("limited_file_handler"),
            )
            # Extract logging config specific sections from AppContext settings

            logging_config_for_manager = {
                "logger": app_context.settings.get_section("logger"),
                "console_handler": app_context.settings.get_section("console_handler"),
                "file_handler": app_context.settings.get_section("file_handler"),
                "limited_file_handler": app_context.settings.get_section("limited_file_handler"),
            }

            # Call the instance's new apply_configuration method
            print("[DEBUG] call apply_configuration")
            cls._instance.apply_configuration(
                cli_log_level=cli_log_level or logging.INFO,  # Provide a default if None
                enable_console_logging=enable_console_logging,
                log_config=logging_config_for_manager,
                translator=app_context.translator,  # Pass translator to manager if it translates log messages
            )

            # Collect any non-critical setup errors from the instance
            cls._initialization_errors.extend(cls._instance.get_instance_errors())
            cls._is_configured = True  # Mark as configured only on success

        except LogHandlerError as e:
            cls._initialization_errors.append(str(e))
            # No need to set _instance to None here, as it was already created.
            # The instance is there, but its configuration failed.
            raise  # Re-raise critical errors
        except Exception as e:
            cls._initialization_errors.append(f"Unexpected error during LoggingManager configuration: {e}")
            raise  # Re-raise unexpected errors

    @classmethod
    def get_initialization_errors(cls) -> list[str]:
        """Exposes initialization errors for testing/debugging."""
        errors = list(cls._initialization_errors)
        if cls._instance:
            errors.extend(cls._instance.get_instance_errors())  # Now calling public method
        return list(set(errors))  # Return unique errors

    @classmethod
    def reset(cls) -> None:  # Or rename to cleanup_instance or similar
        """
        Reset the singleton instance.

        Including clearing any initialization errors.
        This is primarily for testing to ensure a clean state.
        """
        if cls._instance:
            cls._instance.shutdown()  # Call the instance's shutdown method (e.g., to close file handlers)
        cls._instance = None
        cls._initialization_errors.clear()  # Clear any accumulated errors
        cls._is_configured = False  # Reset configured flag
