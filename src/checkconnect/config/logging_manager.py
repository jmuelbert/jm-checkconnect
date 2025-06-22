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
from typing import TYPE_CHECKING, Any, ClassVar, Final, Self, Unpack

import structlog
from platformdirs import user_log_dir
from rich.console import Console

from checkconnect.__about__ import __app_name__
from checkconnect.config.settings_manager import SettingsManager, SettingsManagerSingleton
from checkconnect.config.translation_manager import TranslationManagerSingleton
from checkconnect.exceptions import InvalidLogLevelError, LogDirectoryError, LogHandlerError

if TYPE_CHECKING:
    from types import TracebackType

    from structlog.stdlib import BoundLogger
    from structlog.typing import Processor

# Diese Typen einmalig sichern, bevor Tests patchen
REAL_FILE_HANDLER_TYPE = logging.FileHandler
REAL_ROTATING_FILE_HANDLER_TYPE = logging.handlers.RotatingFileHandler

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)


error_console = Console(file=sys.stderr)


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
    _instance:
    _is_initialized: Boolean True or False
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
    _instance = None
    _is_initialized: bool = False # To prevent re-initialization

    # Constants with improved typing
    APP_NAME: Final[str] = __app_name__
    DEFAULT_LOG_FILENAME: Final[str] = APP_NAME + ".log"
    DEFAULT_LIMITED_LOG_FILENAME: Final[str] = "limited_" + APP_NAME + ".log"
    DEFAULT_MAX_BYTE: Final[int] = 1024 * 1024
    DEFAULT_BACKUP_COUNT: Final[int] = 3

    # Shared structlog processors with proper typing
    SHARED_PROCESSORS: Final[list[Processor]] = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # UTC is good for logs
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # No renderers here! Renderers should be part of the formatter setup.
    ]

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        config: SettingsManager | None = None,
        cli_log_level: int | None = None,
        enable_console_logging: bool = False
    ) -> None:
        """
        Initialize logger.

        Args:
            config: An optional SettingsManager instance.
            cli_log_level: Optional. A logging module level (e.g., logging.DEBUG, logging.INFO)
                           to override the level read from the config file.
        """
        if not self._is_initialized:
            try:
                self.config = config or SettingsManagerSingleton.get_instance()
                self._ = TranslationManagerSingleton.get_instance().gettext
                self.setup_errors = [] # <--- This is what we'll assert on
                self.log_dir = self._ensure_log_dir()  # Can raise LogDirectoryError
                self._active_handlers = []
                self.setup_logging(cli_log_level, enable_console_logging)
                self._is_initialized = True
            except Exception as e:
                msg = self._(f"[bold red]Failed to initialize LoggingManager: {e}[/bold red]")
                error_console.print(msg)
                self.setup_errors.append(msg)
                raise
        else:
            # If already initialized (e.g., second call to __init__ which happens when
            # the singleton holds a reference to a fully initialized object), do nothing.
            # This is important if `get_instance` always calls `LoggingManager()`.
            pass # Or log a debug message

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
        try:
            log_dir = Path(user_log_dir(self.APP_NAME))
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            msg = self._(f"Failed to create log directory {e}")
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
        cli_log_level: int = logging.INFO,
        enable_console_logging: bool = False
    ) -> structlog.stdlib.BoundLogger:
        """
        Configures structlog and Python logging handlers. This method can be called
        publicly to reconfigure logging if necessary, e.g., to change the log level.

        Args:
            cli_log_level:  An optional logging module level (e.g., logging.DEBUG)
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
        if cli_log_level is not None:
            log_level = cli_log_level
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
        self._active_handlers.clear()  # Also clear the internal tracking list

        root_logger.setLevel(log_level)  # Set the root logger's level

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
            foreign_pre_chain=self.SHARED_PROCESSORS,
        )

        file_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),  # JSON for file logging is a good choice
            foreign_pre_chain=self.SHARED_PROCESSORS,
        )

        # Add handlers (now using the `ProcessorFormatter` instances)
        # Add console handler if enabled
        if enable_console_logging:
            try:
                self._add_console_handler(console_formatter, root_logger)
            except LogHandlerError as e:
                msg = self._(f"[bold red]CRITICAL ERROR: Failed to add console handler: {e}[/bold red]")
                error_console.print(msg)
                self.setup_errors.append(msg)
                raise

        try:
            self._add_file_handlers(file_formatter, root_logger)
        except LogHandlerError as e:
            msg = self._(f"[bold blue]WARNING: File logging setup failed: {e}[/bold blue]")
            error_console.print(msg)
            self.setup_errors.append(msg)


        # Configure structlog itself (only if not already configured).
        # `structlog.is_configured()` checks if structlog.configure() has been called successfully.
        if not structlog.is_configured():
            structlog.configure(
                processors=[
                    *self.SHARED_PROCESSORS,
                    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
                ],
                wrapper_class=structlog.make_filtering_bound_logger(log_level),
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=True,  # Recommended for performance
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
        console_handler_config = self.config.get_section("console_handler")
        # Default disabled, add only if CLI is active
        if console_handler_config.get("enabled", False):
            try:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
                self._active_handlers.append(console_handler)
            except (TypeError, AttributeError, MemoryError) as e:
                msg = self._(f"Failed to set up console handler due to formatter or memory issues: {e}")
                raise LogHandlerError(msg) from e
            except Exception as e:  # Catch any other unexpected errors during handler setup
                msg = self._(f"Failed to add console handler: {e}")
                # Instead of `log.exception(msg)`, raise LogHandlerError directly
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
        if file_handler_config.get("enabled", False):  # Default disabled
            file_name = file_handler_config.get(
                "file_name",
                self.DEFAULT_LOG_FILENAME,
            )
            file_name = self._resolve_log_path(file_name)
            try:
                file_handler = logging.FileHandler(file_name)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                self._active_handlers.append(file_handler)
            except (OSError, ValueError) as e:
                msg = self._(
                    f"Failed to create file handler for {file_name}: {e}",
                )
                error_console.print(f"[bold blue]WARNING: File logging setup failed: {msg}[/bold blue]")
                log.warning(msg, exc_info=e)
                self.setup_errors.append(msg)

        # Rotating file handler
        rotating_handler_config = self.config.get_section("limited_file_handler")
        if rotating_handler_config.get("enabled", True):  #  Default enabled
            file_name = rotating_handler_config.get(
                "file_name",
                self.DEFAULT_LIMITED_LOG_FILENAME,
            )
            file_name = self._resolve_log_path(file_name)
            try:
                max_bytes = int(rotating_handler_config.get("max_bytes", 1024))
                backup_count = int(rotating_handler_config.get("backup_count", 5))
                rotating_handler = RotatingFileHandler(
                    file_name,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                )
                rotating_handler.setFormatter(formatter)
                root_logger.addHandler(rotating_handler)
                self._active_handlers.append(rotating_handler)
            except (OSError, ValueError) as e:
                msg = self._(
                    f"Failed to create rotating file handler for {file_name}: {e}",
                )
                error_console.print(f"[bold blue]WARNING: File logging setup failed: {msg}[/bold blue]")
                log.warning(msg, exc_info=e)
                self.setup_errors.append(msg)

    def set_is_initialized(
        self,
        *,
        value: bool = False
    ) -> None:
        self._is_initialized = value

    def shutdown(self) -> None:
        """
        Closes and removes all active handlers from the root logger,
        and performs a comprehensive cleanup of the logging system and structlog.
        """
        root_logger = logging.getLogger()

        # Step 1: Explicitly close and remove all handlers managed by THIS LoggingManager instance
        # It's safer to iterate over a copy of the list that `root_logger.handlers` provides
        handlers_to_remove = []
        for hdlr in root_logger.handlers:
            # Check if this handler was added by *this* manager
            # This is key for responsible cleanup in production, but in tests,
            # you might decide to clear all if your tests don't leave other handlers.
            if hdlr in self._active_handlers:
                try:
                    hdlr.close()
                except (OSError, ValueError, Exception) as e:
                    msg = self._(
                        f"Warning: Failed to close handler {hdlr!r}: {e}"
                    )
                    error_console.print(msg)
                    log.warning(msg, exc_info=e)
                    self.setup_errors.append(msg)
                handlers_to_remove.append(hdlr)

        # Remove the identified handlers from the logger
        for hdlr in handlers_to_remove:
            root_logger.removeHandler(hdlr)

        self._active_handlers.clear() # Clear the internal tracking list

        # Step 2: Perform a broader shutdown of the standard logging module.
        # This flushes buffers and sets internal flags to prevent new handlers
        # from being added or loggers being used after shutdown.
        logging.shutdown()

        # Step 3: Reset structlog's configuration.
        structlog.reset_defaults()

        # Step 4: Ensure the root logger is reset to a clean state.
        # logging.shutdown() usually handles some of this, but explicit resetting
        # can help in complex test scenarios.
        root_logger.setLevel(logging.NOTSET) # Reset level
        # Explicitly clear all handlers from the root logger's list,
        # in case logging.shutdown() or previous steps missed any.
        # This handles handlers that might NOT have been in _active_handlers
        # but were still on the root_logger.
        for hdlr in root_logger.handlers[:]:
            # Ensure any remaining handlers are also closed if they are FileHandlers
            if isinstance(hdlr,  REAL_FILE_HANDLER_TYPE):
                try:
                    hdlr.close()
                except (OSError, ValueError, Exception) as e:
                    msg = self._(
                        f"Warning: Failed to close remaining handler {hdlr!r}: {e}[/bold blue]",
                    )
                    error_console.print(msg)
                    log.warning(msg, exc_info=e)
                    self.setup_errors.append(msg)
            root_logger.removeHandler(hdlr)
        root_logger.handlers.clear() # Ensure the list is truly empty

        # Step 5: Reset singleton flags.
        # These are crucial for your singleton pattern to work correctly across tests.
        LoggingManager._is_initialized = False
        LoggingManager._instance = None # This resets the class-level singleton instance
        # If LoggingManagerSingleton also has an _instance, it should be set to None as well.
        # You're already doing this in cleanup_singletons, which is good.


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
        structlog.get_logger(self.APP_NAME).exception(msg, **kwargs)  # structlog's exception handles exc_info

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
    _initialization_errors: ClassVar[list[str]] = [] # New: To track errors during the singleton's init attempt

    @classmethod
    def get_instance(cls, cli_log_level: int | None = None, enable_console_logging: bool = True) -> LoggingManager:
        if cls._instance is None:
            try:
                cls._instance = LoggingManager(cli_log_level=cli_log_level, enable_console_logging=enable_console_logging)
                # If LoggingManager.__init__ completes successfully,
                # then transfer any errors it collected during its setup
                # (e.g., if file handlers failed but console succeeded)
                if cls._instance.setup_errors:
                    cls._initialization_errors.extend(cls._instance.setup_errors)
            except LogHandlerError as e:
                # If LoggingManager.__init__ fails with a critical error,
                # record it here and re-raise. The instance remains None.
                cls._initialization_errors.append(str(e))
                cls._instance = None # Ensure it's explicitly None if init failed
                raise # Re-raise the original exception
            except Exception as e:
                # Catch any other unexpected errors during LoggingManager init
                cls._initialization_errors.append(f"Unexpected error during LoggingManager init: {e}")
                cls._instance = None
                raise # Re-raise
        return cls._instance

    @classmethod
    def get_initialization_errors(cls) -> list[str]:
        """Exposes initialization errors for testing/debugging."""
        return cls._initialization_errors

    @classmethod
    def reset(cls) -> None: # Or rename to cleanup_instance or similar
        """
        Resets the singleton instance and its associated state,
        including clearing any initialization errors.
        This is primarily for testing to ensure a clean state.
        """
        if cls._instance:
            cls._instance.shutdown() # Call the instance's shutdown method (e.g., to close file handlers)
        cls._instance = None
        cls._initialization_errors.clear() # Clear any accumulated errors
