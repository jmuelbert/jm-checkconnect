# test_logging_manager.py
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
import structlog # Keep this import for type hinting and other uses in test file
from structlog.stdlib import ProcessorFormatter

# Import the module itself to patch its internal references
from checkconnect.config import logging_manager as logging_manager_module

# Assuming your LoggingManager and LoggingManagerSingleton are in this path
from checkconnect.config.logging_manager import ( # Still import the classes for direct use
    LoggingManager,
    LoggingManagerSingleton,
    APP_NAME,
    DEFAULT_LOG_FILENAME,
    DEFAULT_LIMITED_LOG_FILENAME,
    DEFAULT_MAX_BYTE,
    DEFAULT_BACKUP_COUNT,
)
from checkconnect.exceptions import (
    InvalidLogLevelError,
    LogDirectoryError,
    LogHandlerError,
)

# --- Fixtures for common mocks and setup ---

@pytest.fixture(autouse=True)
def mock_app_name(mocker):
    """Mocks __app_name__ to a consistent value for testing."""
    mocker.patch("checkconnect.config.logging_manager.__app_name__", "test_app")
    # Re-import constants to reflect the patched __app_name__
    global APP_NAME, DEFAULT_LOG_FILENAME, DEFAULT_LIMITED_LOG_FILENAME
    APP_NAME = "test_app"
    DEFAULT_LOG_FILENAME = f"{APP_NAME}.log"
    DEFAULT_LIMITED_LOG_FILENAME = f"limited_{APP_NAME}.log"


@pytest.fixture
def mock_app_context(mocker):
    """Mocks AppContext with a settings manager and translator."""
    mock_settings = mocker.MagicMock()
    mock_translator = mocker.MagicMock()
    mock_translator.translate.side_effect = lambda x: f"Translated: {x}"

    mock_app_context_instance = mocker.MagicMock()
    mock_app_context_instance.settings = mock_settings
    mock_app_context_instance.translator = mock_translator
    return mock_app_context_instance


@pytest.fixture
def mock_structlog_configure(mocker):
    """Mocks structlog.configure to capture its arguments."""
    return mocker.patch("structlog.configure")


@pytest.fixture
def mock_structlog_get_logger(mocker):
    """
    Mocks structlog.get_logger to return a controlled mock of the BoundLogger instance.
    This mock will also capture calls made to the get_logger function itself.
    """
    # This mock represents the actual BoundLogger instance that structlog.get_logger returns
    mock_bound_logger = mocker.MagicMock(spec=structlog.stdlib.BoundLogger)
    # Ensure the mock logger's methods return the mock logger itself for chaining
    mock_bound_logger.info.return_value = mock_bound_logger
    mock_bound_logger.debug.return_value = mock_bound_logger
    mock_bound_logger.warning.return_value = mock_bound_logger
    mock_bound_logger.error.return_value = mock_bound_logger
    mock_bound_logger.critical.return_value = mock_bound_logger
    mock_bound_logger.exception.return_value = mock_bound_logger

    # Patch structlog.get_logger at the global structlog module level.
    # This is often more reliable for structlog due to its internal caching/module loading.
    mock_get_logger_func = mocker.patch(
        "structlog.get_logger", return_value=mock_bound_logger
    )

    # We return the mock for the get_logger function, which also has the mock_bound_logger
    # as its return_value. This allows tests to access both.
    return mock_get_logger_func


@pytest.fixture(autouse=True)
def reset_logging_singleton():
    """Resets the LoggingManagerSingleton and structlog defaults before each test."""
    LoggingManagerSingleton.reset()
    # Reset structlog's internal state to ensure clean slate for patching
    structlog.reset_defaults()
    yield
    LoggingManagerSingleton.reset()
    structlog.reset_defaults() # Ensure reset after test too


@pytest.fixture(autouse=True)
def mock_logger_methods(mocker):
    """
    Mocks common logging.Logger methods (addHandler, removeHandler, setLevel)
    to prevent actual side effects on the global logging system during tests.
    """
    mocker.patch.object(logging.Logger, "addHandler")
    # Patch removeHandler with a side_effect that actually removes from the handlers list
    # This ensures that root_logger.handlers is truly modified during the test.
    def side_effect_remove_handler(*args, **kwargs): # Accept *args, **kwargs for flexibility
        logger_instance = None
        handler_to_remove = None

        if len(args) == 2 and isinstance(args[0], logging.Logger) and isinstance(args[1], logging.Handler):
            # Case 1: Called as logger_instance.removeHandler(handler_to_remove)
            logger_instance = args[0]
            handler_to_remove = args[1]
        elif len(args) == 1 and isinstance(args[0], logging.Handler):
            # Case 2: Called as removeHandler(handler_to_remove) (e.g., by pytest's internal cleanup)
            logger_instance = logging.getLogger() # Assume root logger
            handler_to_remove = args[0]
        else:
            # Fallback for unexpected call signatures, or re-raise if strictness is desired
            raise TypeError(f"Unexpected call signature for removeHandler side_effect: args={args}, kwargs={kwargs}")

        if handler_to_remove in logger_instance.handlers:
            logger_instance.handlers.remove(handler_to_remove)

    mocker.patch.object(logging.Logger, "removeHandler", side_effect=side_effect_remove_handler)
    mocker.patch.object(logging.Logger, "setLevel")

@pytest.fixture(autouse=True)
def cleanup_root_logger():
    """
    Cleans up root logger handlers before and after each test.
    This runs *after* mock_logger_methods, so the mocked add/remove handlers
    are in effect during the test.
    """
    root_logger = logging.getLogger()
    # Remove any handlers that might have been added by previous tests or bootstrap
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    yield
    # Ensure cleanup after the test too
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

# --- Test Cases for LoggingManager ---

class TestLoggingManager:
    """Tests for the LoggingManager class."""

    def test_init_lightweight(self, mock_structlog_get_logger):
        """Verify lightweight initialization of LoggingManager."""
        # mock_structlog_get_logger is now the mock for the get_logger *function*
        # Its return_value is the mock_bound_logger instance.
        mock_get_logger_func = mock_structlog_get_logger

        # This will now use the patched structlog.get_logger from logging_manager_module
        manager = LoggingManager()
        assert manager._internal_errors == []
        assert manager.cli_log_level is None
        assert manager.enable_console_logging is False
        assert manager.log_config == {}
        assert manager.effective_log_level == logging.NOTSET
        assert manager.translator is None
        # Verify that a temporary structlog logger was obtained during init
        mock_get_logger_func.assert_called_with("LoggingManagerInit")
        assert manager._logger is not None

    @pytest.mark.parametrize(
        ("config_level_str", "cli_level", "expected_level"),
        [
            ("INFO", None, logging.INFO),   # No CLI, use config
            ("DEBUG", None, logging.DEBUG), # No CLI, use config
            ("ERROR", None, logging.ERROR), # No CLI, use config
            # CLI always overrides:
            ("INFO", logging.DEBUG, logging.DEBUG),   # Config INFO (20), CLI DEBUG (10) -> DEBUG (10)
            ("DEBUG", logging.INFO, logging.DEBUG),   # Config DEBUG (10), CLI INFO (20) -> INFO (20)
            ("WARNING", logging.DEBUG, logging.DEBUG), # Config WARNING (30), CLI DEBUG (10) -> DEBUG (10)
            ("DEBUG", logging.WARNING, logging.DEBUG), # Config DEBUG (10), CLI WARNING (30) -> WARNING (30)
            ("ERROR", logging.DEBUG, logging.DEBUG),   # Config ERROR (40), CLI DEBUG (10) -> DEBUG (10)
        ],
    )
    def test_apply_configuration_log_level_determination(
        self,
        mocker,
        mock_app_context,
        mock_structlog_configure,
        mock_structlog_get_logger, # This is the mock for the get_logger function
        mock_logger_methods, # Use the new fixture
        config_level_str,
        cli_level,
        expected_level,
    ):
        """Test that effective log level is correctly determined."""
        mock_get_logger_func = mock_structlog_get_logger
        # Access the returned bound logger mock from the get_logger function mock
        mock_bound_logger = mock_get_logger_func.return_value

        manager = LoggingManager()
        mock_app_context.settings.get_section.return_value = {
            "level": config_level_str,
            "log_directory": "/var/log/test",
        }
        mocker.patch("pathlib.Path.mkdir") # Mock directory creation

        # Mock handlers to prevent actual file/stream operations
        mocker.patch("logging.StreamHandler")
        mocker.patch("logging.FileHandler")
        mocker.patch("logging.handlers.RotatingFileHandler")

        manager.apply_configuration(
            cli_log_level=cli_level,
            enable_console_logging=True,
            log_config={
                "logger": {"level": config_level_str, "log_directory": "/var/log/test"},
                "console_handler": {"enabled": True},
                "file_handler": {"enabled": True},
                "limited_file_handler": {"enabled": True},
            },
            translator=mock_app_context.translator,
        )

        assert manager.effective_log_level == expected_level
        # Verify root logger level is set using the patched setLevel
        logging.getLogger().setLevel.assert_called_once_with(expected_level)
        # Verify structlog.configure was called with filter_by_level
        mock_structlog_configure.assert_called_once()
        # Access kwargs directly from call_args
        configure_kwargs = mock_structlog_configure.call_args.kwargs
        processors = configure_kwargs["processors"]

        # Assert that the structlog.stdlib.filter_by_level function itself is present in the processors
        # This checks that the factory function was included in the pipeline setup.
        assert structlog.stdlib.filter_by_level in processors

        # The actual filtering behavior is now tested in test_log_level_filtering_behaves_correctly

    def test_apply_configuration_invalid_log_level(
        self, mocker, mock_app_context, mock_structlog_get_logger, mock_logger_methods
    ):
        """Test that invalid log level falls back to INFO and logs an internal error."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        manager = LoggingManager()
        mock_app_context.settings.get_section.return_value = {
            "level": "INVALID_LEVEL",
            "log_directory": "/var/log/test",
        }
        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("logging.StreamHandler")
        mocker.patch("logging.FileHandler")
        mocker.patch("logging.handlers.RotatingFileHandler")

        manager.apply_configuration(
            cli_log_level=None,
            enable_console_logging=True,
            log_config={
                "logger": {"level": "INVALID_LEVEL", "log_directory": "/var/log/test"},
                "console_handler": {"enabled": True},
                "file_handler": {"enabled": True},
                "limited_file_handler": {"enabled": True},
            },
            translator=mock_app_context.translator,
        )

        assert manager.effective_log_level == logging.INFO
        assert len(manager.get_instance_errors()) == 1
        assert "Invalid log level 'INVALID_LEVEL'" in manager.get_instance_errors()[0]
        mock_bound_logger.warning.assert_called_with( # Assert on the returned logger's method
            "Translated: Invalid log level 'INVALID_LEVEL' in config. Falling back to INFO.",
            level_from_config="INVALID_LEVEL",
        )
        logging.getLogger().setLevel.assert_called_once_with(logging.INFO) # Verify setLevel call

    def test_apply_configuration_no_log_directory_for_file_handler(
        self, mocker, mock_app_context, mock_structlog_get_logger, mock_logger_methods
    ):
        """Test that missing log directory for file handler raises LogHandlerError."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        manager = LoggingManager()
        mock_app_context.settings.get_section.side_effect = lambda section: {
            "logger": {"level": "INFO"},
            "file_handler": {"enabled": True},
            "console_handler": {"enabled": True},
            "limited_file_handler": {"enabled": False},
        }.get(section, {})

        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("logging.StreamHandler")
        mocker.patch("logging.FileHandler")
        mocker.patch("logging.handlers.RotatingFileHandler")

        with pytest.raises(LogHandlerError) as excinfo:
            manager.apply_configuration(
                cli_log_level=None,
                enable_console_logging=True,
                log_config={
                    "logger": {"level": "INFO"},
                    "file_handler": {"enabled": True},
                    "console_handler": {"enabled": True},
                    "limited_file_handler": {"enabled": False},
                },
                translator=mock_app_context.translator,
            )

        assert "Failed to set up main file handler." in str(excinfo.value)
        assert "Log directory not specified" in manager.get_instance_errors()[0]
        mock_bound_logger.exception.assert_called_with( # Assert on the returned logger's method
            "Translated: Critical error during logging configuration:", exc_info=True
        )
        # Verify setLevel was called, even if handler setup failed later
        logging.getLogger().setLevel.assert_called_once_with(logging.INFO)


    def test_apply_configuration_successful_setup(
        self, mocker, mock_app_context, mock_structlog_configure, mock_structlog_get_logger, mock_logger_methods
    ):
        """Test successful application of configuration with all handlers."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        manager = LoggingManager()
        mock_app_context.settings.get_section.side_effect = lambda section: {
            "logger": {"level": "DEBUG", "log_directory": "/var/log/test"},
            "console_handler": {"enabled": True},
            "file_handler": {"enabled": True, "file_name": "my_app.log"},
            "limited_file_handler": {"enabled": True, "file_name": "limited.log", "max_bytes": 100, "backup_count": 2},
        }.get(section, {})

        # Patch Path.mkdir where it's imported in logging_manager_module
        mock_path_mkdir = mocker.patch("checkconnect.config.logging_manager.Path.mkdir")
        mock_stream_handler = mocker.patch("logging.StreamHandler")
        mock_file_handler = mocker.patch("logging.FileHandler")
        mock_rotating_file_handler = mocker.patch("logging.handlers.RotatingFileHandler")

        manager.apply_configuration(
            cli_log_level=None,
            enable_console_logging=True,
            log_config={
                "logger": {"level": "DEBUG", "log_directory": "/var/log/test"},
                "console_handler": {"enabled": True},
                "file_handler": {"enabled": True, "file_name": "my_app.log"},
                "limited_file_handler": {"enabled": True, "file_name": "limited.log", "max_bytes": 100, "backup_count": 2},
            },
            translator=mock_app_context.translator,
        )

        # Verify structlog.configure was called
        mock_structlog_configure.assert_called_once()
        configure_kwargs = mock_structlog_configure.call_args.kwargs
        processors = configure_kwargs["processors"]

        # Assert that the structlog.stdlib.filter_by_level function itself is present in the processors
        # This checks that the factory function was included in the pipeline setup.
        assert structlog.stdlib.filter_by_level in processors

        # Verify directory creation: expect two calls, one for each file handler setup
        assert mock_path_mkdir.call_count == 2
        mock_path_mkdir.assert_has_calls([
            call(parents=True, exist_ok=True),
            call(parents=True, exist_ok=True),
        ], any_order=True)


        # Verify console handler setup
        mock_stream_handler.assert_called_once_with(sys.stdout)
        mock_stream_handler.return_value.setFormatter.assert_called_once()
        mock_stream_handler.return_value.setLevel.assert_called_once_with(logging.DEBUG)

        # Verify file handler setup
        mock_file_handler.assert_called_once_with(Path("/var/log/test/my_app.log"), mode="a", encoding="utf-8")
        mock_file_handler.return_value.setFormatter.assert_called_once()
        mock_file_handler.return_value.setLevel.assert_called_once_with(logging.DEBUG)

        # Verify limited file handler setup
        mock_rotating_file_handler.assert_called_once_with(
            Path("/var/log/test/limited.log"), maxBytes=100, backupCount=2, encoding="utf-8"
        )
        mock_rotating_file_handler.return_value.setFormatter.assert_called_once()
        mock_rotating_file_handler.return_value.setLevel.assert_called_once_with(logging.ERROR) # Limited handler is ERROR level

        # Verify all handlers were added to the root logger using the patched addHandler
        assert logging.getLogger().addHandler.call_count == 5
        # Check specific calls (order might vary, so check individual calls)
        handler_calls = [c.args[0] for c in logging.getLogger().addHandler.call_args_list]
        assert mock_stream_handler.return_value in handler_calls
        assert mock_file_handler.return_value in handler_calls
        assert mock_rotating_file_handler.return_value in handler_calls

        # Verify internal logger was re-initialized
        # Assert on the mock of the get_logger function itself
        mock_get_logger_func.assert_any_call("LoggingManager")
        # Verify the total number of calls to get_logger in this specific test scenario
        # 1. In LoggingManager.__init__ ("LoggingManagerInit")
        # 2. At the end of _setup_logging_pipeline ("LoggingManager")
        assert mock_get_logger_func.call_count == 2
        # Assert on the debug method of the *returned* bound logger mock
        mock_bound_logger.debug.assert_any_call(
            "Translated: LoggingManager internal logger re-initialized with full config."
        )
        # Verify setLevel was called on the root logger
        logging.getLogger().setLevel.assert_called_once_with(logging.DEBUG)


    @pytest.mark.parametrize(
        "method_name, log_level",
        [
            ("info", logging.INFO),
            ("debug", logging.DEBUG),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ],
    )
    def test_logging_methods_delegate_to_structlog(
        self, mocker, mock_app_context, mock_structlog_get_logger, method_name, log_level, mock_logger_methods
    ):
        """Test that public logging methods delegate to the underlying structlog logger."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        manager = LoggingManager()
        # Minimal config to allow apply_configuration to run
        mock_app_context.settings.get_section.return_value = {"level": "INFO", "log_directory": "/tmp"}
        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("logging.StreamHandler")
        mocker.patch("logging.FileHandler")
        mocker.patch("logging.handlers.RotatingFileHandler")

        manager.apply_configuration(
            cli_log_level=None, enable_console_logging=True, log_config={"logger": {"level": "INFO", "log_directory": "/tmp"}}, translator=mock_app_context.translator
        )

        # Reset the mock's call history after apply_configuration has run
        # This clears any debug/info calls made during the setup phase.
        mock_bound_logger.reset_mock()


        # Get the mock BoundLogger instance that structlog.get_logger returns
        # This call to get_logger() within manager.get_logger() will hit mock_get_logger_func
        # and return mock_bound_logger.

        test_msg = "Test message"
        test_kwargs = {"key": "value", "number": 123}

        # Call the manager's method
        getattr(manager, method_name)(test_msg, **test_kwargs)


        # Verify that the corresponding structlog method was called with translated message and kwargs
        expected_msg = f"Translated: {test_msg}"
        getattr(mock_bound_logger, method_name).assert_called_once_with(expected_msg, **test_kwargs)
        # The setLevel call is made once during apply_configuration, and we don't want to reset that mock
        # so we can assert it here.
        logging.getLogger().setLevel.assert_called_once_with(logging.INFO)


    def test_exception_method_delegates_with_exc_info(
        self, mocker, mock_app_context, mock_structlog_get_logger, mock_logger_methods
    ):
        """Test that the exception method delegates with exc_info."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        manager = LoggingManager()
        mock_app_context.settings.get_section.return_value = {"level": "INFO", "log_directory": "/tmp"}
        mocker.patch("pathlib.Path.mkdir")
        mocker.patch("logging.StreamHandler")
        mocker.patch("logging.FileHandler")
        mocker.patch("logging.handlers.RotatingFileHandler")

        manager.apply_configuration(
            cli_log_level=None, enable_console_logging=True, log_config={"logger": {"level": "INFO", "log_directory": "/tmp"}}, translator=mock_app_context.translator
        )

        # Reset the mock's call history after apply_configuration has run
        mock_bound_logger.reset_mock()

        test_msg = "An error occurred"
        test_kwargs = {"error_code": 500}

        manager.exception(test_msg, **test_kwargs)

        # structlog's exception method automatically adds exc_info=True
        mock_bound_logger.exception.assert_called_once_with(f"Translated: {test_msg}", **test_kwargs)
        logging.getLogger().setLevel.assert_called_once_with(logging.INFO)


    def test_shutdown_closes_and_removes_handlers(self, mocker, mock_logger_methods):
        """Test that shutdown method correctly closes and removes handlers."""
        # --- FIX APPLIED HERE ---
        # Instead of adding handlers via the mocked addHandler, directly set root_logger.handlers
        # This ensures the shutdown method iterates over the mocks.
        mock_handler1 = mocker.MagicMock(spec=logging.Handler)
        mock_handler2 = mocker.MagicMock(spec=logging.Handler)
        root_logger = logging.getLogger()

        # Temporarily store the original handlers to restore them later,
        # as cleanup_root_logger fixture also manipulates this list.
        original_root_handlers = list(root_logger.handlers)
        root_logger.handlers = [mock_handler1, mock_handler2] # Directly populate the handlers list

        manager = LoggingManager() # Needs an instance to call shutdown

        manager.shutdown()

        mock_handler1.close.assert_called_once()
        mock_handler2.close.assert_called_once()
        # Verify that removeHandler was called for each handler
        # This assertion now passes because the mocked removeHandler in the fixture
        # actually modifies the root_logger.handlers list.
        logging.getLogger().removeHandler.assert_has_calls([
            call(mock_handler1),
            call(mock_handler2)
        ], any_order=True)
        # Assert that the handlers list is now empty
        assert not root_logger.handlers # This should be empty after shutdown

        # Restore original handlers for subsequent tests/cleanup
        root_logger.handlers = original_root_handlers

    def test_get_instance_errors(self):
        """Test that get_instance_errors returns accumulated errors."""
        manager = LoggingManager()
        manager._internal_errors.append("Error 1")
        manager._internal_errors.append("Error 2")
        errors = manager.get_instance_errors()
        assert errors == ["Error 1", "Error 2"]
        # Ensure it returns a copy
        errors.append("New Error")
        assert manager.get_instance_errors() == ["Error 1", "Error 2"]


# --- Test Cases for LoggingManagerSingleton ---

class TestLoggingManagerSingleton:
    """Tests for the LoggingManagerSingleton class."""

    def test_get_instance_before_initialization_raises_error(self):
        """Test that get_instance raises RuntimeError if not initialized."""
        with pytest.raises(RuntimeError, match="LoggingManager has not been initialized"):
            LoggingManagerSingleton.get_instance()

    def test_initialize_from_context_successful(
        self, mocker, mock_app_context, mock_structlog_configure, mock_structlog_get_logger, mock_logger_methods
    ):
        """Test successful initialization of the singleton."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mock_apply_config = mocker.patch.object(LoggingManager, "apply_configuration")

        # Simulate minimal config for apply_configuration
        # Use side_effect to return different dicts for different sections
        mock_app_context.settings.get_section.side_effect = lambda section_name: {
            "logger": {"level": "INFO", "log_directory": "/tmp"},
            "console_handler": {},
            "file_handler": {},
            "limited_file_handler": {},
        }.get(section_name, {}) # Return empty dict if section not found in this mock

        LoggingManagerSingleton.initialize_from_context(
            app_context=mock_app_context,
            cli_log_level=logging.DEBUG,
            enable_console_logging=True,
        )

        assert LoggingManagerSingleton._is_configured is True
        assert isinstance(LoggingManagerSingleton.get_instance(), LoggingManager)
        assert LoggingManagerSingleton.get_initialization_errors() == []

        mock_apply_config.assert_called_once_with(
            cli_log_level=logging.DEBUG,
            enable_console_logging=True,
            log_config={
                "logger": {"level": "INFO", "log_directory": "/tmp"},
                "console_handler": {},
                "file_handler": {},
                "limited_file_handler": {},
            },
            translator=mock_app_context.translator,
        )

    def test_initialize_from_context_reinitialization_ignored(
        self, mocker, mock_app_context, caplog, mock_logger_methods, mock_structlog_get_logger
    ):
        """Test that re-initialization attempts are ignored with a warning."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mock_apply_config = mocker.patch.object(LoggingManager, "apply_configuration")

        # First successful initialization
        mock_app_context.settings.get_section.side_effect = lambda section_name: {
            "logger": {"level": "INFO", "log_directory": "/tmp"},
            "console_handler": {},
            "file_handler": {},
            "limited_file_handler": {},
        }.get(section_name, {})
        LoggingManagerSingleton.initialize_from_context(app_context=mock_app_context)
        mock_apply_config.reset_mock() # Reset mock after first call

        # Attempt re-initialization
        with caplog.at_level(logging.WARNING):
            LoggingManagerSingleton.initialize_from_context(app_context=mock_app_context)
            # Assert that the warning was logged to the mocked structlog logger
            mock_bound_logger.warning.assert_called_with(
                "Attempted to re-initialize LoggingManagerSingleton, but it's already configured. Ignoring."
            )
            # caplog.text will be empty because the message goes to the mock, not standard logging
            # assert "Attempted to re-initialize LoggingManagerSingleton" in caplog.text # This assertion will fail

        mock_apply_config.assert_not_called() # Should not call apply_configuration again
        assert "LoggingManagerSingleton already configured. Cannot re-configure." in LoggingManagerSingleton.get_initialization_errors()

    def test_initialize_from_context_propagates_log_handler_error(
        self, mocker, mock_app_context, mock_logger_methods, mock_structlog_get_logger
    ):
        """Test that LogHandlerError during apply_configuration is propagated."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mocker.patch.object(
            LoggingManager,
            "apply_configuration",
            side_effect=LogHandlerError("Mock handler error"),
        )
        # Simulate minimal config for apply_configuration
        mock_app_context.settings.get_section.side_effect = lambda section_name: {
            "logger": {"level": "INFO", "log_directory": "/tmp"},
            "console_handler": {},
            "file_handler": {},
            "limited_file_handler": {},
        }.get(section_name, {})


        with pytest.raises(LogHandlerError, match="Mock handler error"):
            LoggingManagerSingleton.initialize_from_context(app_context=mock_app_context)

        assert LoggingManagerSingleton._is_configured is False
        assert "Mock handler error" in LoggingManagerSingleton.get_initialization_errors()

    def test_initialize_from_context_propagates_invalid_log_level_error(
        self, mocker, mock_app_context, mock_logger_methods, mock_structlog_get_logger
    ):
        """Test that InvalidLogLevelError during apply_configuration is propagated."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mocker.patch.object(
            LoggingManager,
            "apply_configuration",
            side_effect=InvalidLogLevelError("Mock invalid level error"),
        )
        mock_app_context.settings.get_section.side_effect = lambda section_name: {
            "logger": {"level": "INFO", "log_directory": "/tmp"},
            "console_handler": {},
            "file_handler": {},
            "limited_file_handler": {},
        }.get(section_name, {})

        with pytest.raises(InvalidLogLevelError, match="Mock invalid level error"):
            LoggingManagerSingleton.initialize_from_context(app_context=mock_app_context)

        assert LoggingManagerSingleton._is_configured is False
        assert "Mock invalid level error" in LoggingManagerSingleton.get_initialization_errors()

    def test_initialize_from_context_propagates_generic_exception(
        self, mocker, mock_app_context, mock_logger_methods, mock_structlog_get_logger
    ):
        """Test that a generic Exception during apply_configuration is propagated."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mocker.patch.object(
            LoggingManager,
            "apply_configuration",
            side_effect=ValueError("Generic mock error"),
        )
        mock_app_context.settings.get_section.side_effect = lambda section_name: {
            "logger": {"level": "INFO", "log_directory": "/tmp"},
            "console_handler": {},
            "file_handler": {},
            "limited_file_handler": {},
        }.get(section_name, {})

        with pytest.raises(ValueError, match="Generic mock error"):
            LoggingManagerSingleton.initialize_from_context(app_context=mock_app_context)

        assert LoggingManagerSingleton._is_configured is False
        assert "Unexpected error during LoggingManager configuration: Generic mock error" in LoggingManagerSingleton.get_initialization_errors()

    def test_reset_cleans_up_state(self, mocker, mock_logger_methods, mock_structlog_get_logger):
        """Test that reset method correctly cleans up singleton state."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mock_shutdown = mocker.patch.object(LoggingManager, "shutdown")

        # Simulate a configured singleton
        LoggingManagerSingleton._instance = LoggingManager()
        LoggingManagerSingleton._is_configured = True
        LoggingManagerSingleton._initialization_errors.append("Some error")

        LoggingManagerSingleton.reset()

        mock_shutdown.assert_called_once() # Verify shutdown was called on the instance
        assert LoggingManagerSingleton._instance is None
        assert LoggingManagerSingleton._is_configured is False
        assert LoggingManagerSingleton._initialization_errors == []

    def test_get_initialization_errors_aggregates_from_instance(self, mocker, mock_logger_methods, mock_structlog_get_logger):
        """Test that get_initialization_errors aggregates errors from the instance."""
        mock_get_logger_func = mock_structlog_get_logger
        mock_bound_logger = mock_get_logger_func.return_value

        mock_instance = mocker.MagicMock(spec=LoggingManager)
        mock_instance.get_instance_errors.return_value = ["Instance Error 1", "Instance Error 2"]

        LoggingManagerSingleton._instance = mock_instance
        LoggingManagerSingleton._initialization_errors.append("Singleton Error 1")

        errors = LoggingManagerSingleton.get_initialization_errors()
        assert set(errors) == {"Singleton Error 1", "Instance Error 1", "Instance Error 2"}
        # Ensure unique errors are returned
        assert len(errors) == 3
