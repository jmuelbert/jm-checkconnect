# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Pytest-mock test suite for the LoggingManager class.

This module contains comprehensive tests for the LoggingManager, ensuring its
correct behavior across various scenarios, including successful configurations,
error handling, and proper resource cleanup. It uses pytest-mock for
mocking external dependencies and internal methods.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
import structlog.stdlib

from checkconnect.config.logging_manager import (
    LoggingManager,
    LoggingManagerSingleton,
)

# Assuming the LoggingManager and its exceptions are in a file named `logging_manager.py`
# Adjust the import path if your file structure is different.

if TYPE_CHECKING:
    from collections.abc import Generator


# --- fixtures ---
# Define your patch paths
# Patch the 'logging' module itself as imported in logging_manager.py
# This is crucial for correctly patching 'handlers' and 'FileHandler'
LOGGING_MODULE_PATH_IN_MANAGER = "checkconnect.config.logging_manager.logging"

# Patch the handlers submodule and FileHandler/RotatingFileHandler within that submodule.
# Note the change: we're patching these AS ATTRIBUTES of the 'logging' module within logging_manager.
FILE_HANDLER_PATCH_PATH = "FileHandler"
ROTATING_FILE_HANDLER_PATCH_PATH = "handlers.RotatingFileHandler"

PROCESSOR_FORMATTER_PATCH_PATH = "checkconnect.config.logging_manager.ProcessorFormatter"

APP_NAME = "test"


@pytest.fixture
def mock_settings_manager_instance(tmp_path: Path) -> MagicMock:
    """
    Creates a mock `SettingsManager` with a predefined test configuration.

    This fixture provides a `MagicMock` that mimics the behavior of `SettingsManager`,
    allowing tests to control the application's settings without loading actual
    configuration files.

    Returns:
    -------
        A `MagicMock` instance configured to simulate `SettingsManager`.
    """
    mock_config_instance = MagicMock()

    # Define a consistent log directory for testing
    test_log_directory = "test_logs"

    mock_config_instance.get_section.side_effect = lambda section: {
        "logger": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_directory": test_log_directory,  # This is now read from here
            "output_format": "console",
        },
        "console_handler": {"enabled": False},
        "file_handler": {
            "enabled": True,
            "file_name": APP_NAME + ".log",
        },
        "limited_file_handler": {
            "enabled": True,
            "file_name": "limited_" + APP_NAME + ".log",
            "max_bytes": 1024,
            "backup_count": 5,
        },
    }.get(section, {})

    mock_config_instance.get_full_config.return_value = {
        "logger": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_directory": test_log_directory,  # This is now read from here
            "output_format": "console",
        },
        "console_handler": {"enabled": False},
        "file_handler": {
            "enabled": True,
            "file_name": "app.log",
        },
        "limited_file_handler": {
            "enabled": True,
            "file_name": "app-limited.log",
            "max_bytes": 1024 * 1024,
            "backup_count": 3,
        },
        "stream_handler": {"enabled": False},
    }

    # Add a helper attribute to the mock for convenience in tests
    mock_config_instance.get_full_logging_config.return_value = {
        "logger": mock_config_instance.get_section("logger"),
        "console_handler": mock_config_instance.get_section("console_handler"),
        "file_handler": mock_config_instance.get_section("file_handler"),
        "limited_file_handler": mock_config_instance.get_section("limited_file_handler"),
    }
    return mock_config_instance


@pytest.fixture
def mock_logging_manager_dependencies(
    tmp_path: Path, mock_settings_manager_instance: MagicMock
) -> Generator[dict[str, MagicMock], None, None]:
    """
    Mocks dependencies for LoggingManager including Path, file handlers, translation,
    formatter, and logger factory. Ensures consistent and isolated behavior in tests.
    """
    log_config = mock_settings_manager_instance.get_section("logger")
    log_dir_name = log_config.get("log_directory", "default_logs")

    actual_log_dir = tmp_path / log_dir_name
    actual_log_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch("checkconnect.config.logging_manager.Path") as mock_path_class,
        patch("checkconnect.config.logging_manager.TranslationManagerSingleton") as mock_translation_singleton_cls,
        patch("checkconnect.config.logging_manager.structlog.stdlib.LoggerFactory") as mock_logger_factory_cls,
        patch("checkconnect.config.logging_manager.logging.FileHandler") as mock_file_handler_cls,
        patch("checkconnect.config.logging_manager.logging.StreamHandler") as mock_stream_handler_cls,
        patch(
            "checkconnect.config.logging_manager.logging.handlers.RotatingFileHandler"
        ) as mock_rotating_file_handler_cls,  # ✅ corrected
        patch("checkconnect.config.logging_manager.logging.getLogger") as mock_get_logger,
        patch(PROCESSOR_FORMATTER_PATCH_PATH) as mock_formatter_cls,
    ):
        # Translation mocks
        mock_translation_instance = MagicMock()
        mock_translation_instance.gettext.side_effect = lambda msg: f"translated: {msg}"

        mock_translation_manager = MagicMock()
        mock_translation_manager.translation = mock_translation_instance
        mock_translation_manager._ = mock_translation_instance.gettext
        mock_translation_manager.gettext = mock_translation_instance.gettext

        mock_translation_singleton_cls.get_instance.return_value = mock_translation_manager

        # Handlers
        mock_file_handler_instance = MagicMock(name="FileHandler")
        mock_file_handler_cls.return_value = mock_file_handler_instance

        mock_rotating_handler_instance = MagicMock(name="RotatingFileHandler")
        mock_rotating_file_handler_cls.return_value = mock_rotating_handler_instance

        mock_stream_handler_instance = MagicMock(name="StreamHandler")
        mock_stream_handler_cls.return_value = mock_stream_handler_instance

        # Formatter and factory
        mock_formatter_instance = MagicMock(name="Formatter")
        mock_formatter_cls.return_value = mock_formatter_instance

        mock_logger_factory_instance = MagicMock(name="LoggerFactoryInstance")
        mock_logger_factory_cls.return_value = mock_logger_factory_instance

        # --- Path patching ---
        def path_side_effect(p: str | Path) -> MagicMock:
            target = actual_log_dir if Path(p).name == log_dir_name else tmp_path / p
            mock_path = MagicMock(spec=Path)
            mock_path.__fspath__.return_value = str(target)
            mock_path.__str__.return_value = str(target)
            mock_path.exists.return_value = target.exists()
            mock_path.mkdir.return_value = None
            mock_path.name = target.name
            mock_path.__truediv__.side_effect = lambda sub: target / sub
            return mock_path

        mock_path_class.side_effect = path_side_effect

        # # Path mock
        # def path_side_effect(p: str | Path) -> MagicMock:
        #     target = actual_log_dir if Path(p).name == log_dir_name else tmp_path / p
        #     mock_path = MagicMock(spec=Path)
        #     mock_path.__fspath__.return_value = str(target)
        #     mock_path.__str__.return_value = str(target)
        #     mock_path.exists.return_value = target.exists()
        #     mock_path.mkdir.return_value = None
        #     mock_path.name = target.name

        #     # Mock __truediv__ to return another mocked Path object
        #     def truediv_mock(sub):
        #         sub_target = target / sub
        #         mock_sub_path = MagicMock(spec=Path)
        #         mock_sub_path.__fspath__.return_value = str(sub_target)
        #         mock_sub_path.__str__.return_value = str(sub_target)
        #         mock_sub_path.exists.return_value = sub_target.exists()
        #         mock_sub_path.mkdir.return_value = None
        #         mock_sub_path.name = sub_target.name
        #         mock_sub_path.parent = mock_path  # Set parent back to mock_path for .parent calls
        #         return mock_sub_path

        #     mock_path.__truediv__.side_effect = truediv_mock

        #    # Add .parent attribute needed for log_file_path.parent.mkdir()
        #     mock_path.parent = MagicMock(spec=Path)
        #     mock_path.parent.mkdir.return_value = None

        #    return mock_path

        # mock_path_class.side_effect = path_side_effect

        yield {
            "mock_path_class": mock_path_class,
            "mock_file_handler_class": mock_file_handler_cls,
            "mock_rotating_file_handler_class": mock_rotating_file_handler_cls,
            "mock_stream_handler_class": mock_stream_handler_cls,
            "mock_file_handler_instance": mock_file_handler_instance,
            "mock_rotating_file_handler_instance": mock_rotating_handler_instance,
            "mock_stream_handler_instance": mock_stream_handler_instance,
            "mock_processor_formatter_class": mock_formatter_cls,
            "mock_processor_formatter_instance": mock_formatter_instance,
            "mock_logger_factory_class": mock_logger_factory_cls,
            "mock_logger_factory_instance": mock_logger_factory_instance,
            "mock_translation_manager_singleton_cls": mock_translation_singleton_cls,
            "mock_translation_manager_instance": mock_translation_manager,
            "mock_get_logger": mock_get_logger,
        }


@pytest.fixture
def mock_structlog() -> Generator[dict[str, MagicMock], None, None]:
    """
    Fixture to mock structlog for tests focused on LoggingManager's interaction
    with structlog configuration methods (configure, reset_defaults, get_logger).
    It simulates a base configuration and resets mocks for clear assertions.
    """
    with patch("checkconnect.config.logging_manager.structlog") as mock_structlog_actual:
        mock_configure = MagicMock()
        mock_is_configured = MagicMock(return_value=False)
        mock_get_logger = MagicMock()
        mock_reset_defaults = MagicMock()

        mock_structlog_actual.configure = mock_configure
        mock_structlog_actual.is_configured = mock_is_configured
        mock_structlog_actual.get_logger = mock_get_logger
        mock_structlog_actual.reset_defaults = mock_reset_defaults

        # Hier speichern wir die letzten Aufruf-Keyword-Argumente für spätere Prüfung
        mock_configure.call_args = None

        def configure_side_effect(*args, **kwargs):
            mock_configure.call_args = kwargs

        mock_configure.side_effect = configure_side_effect

        mock_reset_defaults.side_effect = lambda: None

        # Simuliere Basiskonfiguration (optional)
        mock_reset_defaults()
        mock_structlog_actual.configure(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
            ],
            logger_factory=MagicMock(),
            wrapper_class=MagicMock(),
            cache_logger_on_first_use=True,
        )

        mock_configure.reset_mock()
        mock_is_configured.reset_mock()
        mock_get_logger.reset_mock()
        mock_reset_defaults.reset_mock()

        yield {
            "configure": mock_configure,
            "is_configured": mock_is_configured,
            "get_logger": mock_get_logger,
            "structlog_module": mock_structlog_actual,
            "reset_defaults": mock_reset_defaults,
        }


# --- Tests for LoggingManager ---
class TestLoggingManager:
    """
    Test suite for the LoggingManager class.
    """

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_logging_manager_init_and_configure_from_settings(
        self,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Test LoggingManager initialization and configuration from settings.
        Ensures structlog, file, rotating, and stream handlers are correctly set up.
        """
        # Structlog mocks
        mock_get_logger = mock_structlog["get_logger"]
        mock_configure = mock_structlog["configure"]

        # LoggingManager dependencies
        d = mock_logging_manager_dependencies
        mock_translation = d["mock_translation_manager_instance"]
        mock_translation_singleton = d["mock_translation_manager_singleton_cls"]

        # Instantiate LoggingManager
        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(
                config=mock_settings_manager_instance,
                cli_log_level=logging.DEBUG,
                enable_console_logging=True,
            )

        # Verify translation setup
        mock_translation_singleton.get_instance.assert_called_once()
        mock_translation.gettext.assert_called()

        # Base assertions
        assert manager.cli_log_level == logging.DEBUG
        assert manager.enable_console_logging is True
        assert manager.setup_errors == []
        assert manager.logger is mock_get_logger.return_value
        mock_get_logger.assert_called_once_with("checkconnect.config.logging_manager")

        # Configure from settings
        full_config = mock_settings_manager_instance.get_full_config.return_value
        manager.configure_from_settings(full_config, logger_factory=d["mock_logger_factory_class"])

        # structlog.configure() called with correct arguments
        mock_configure.assert_called_once()
        config_kwargs = mock_configure.call_args or {}
        assert config_kwargs["cache_logger_on_first_use"] is True
        assert config_kwargs["logger_factory"] is d["mock_logger_factory_class"].return_value
        d["mock_logger_factory_class"].assert_called_once()

        processors = config_kwargs.get("processors", [])
        assert any(callable(p) for p in processors)
        assert any("add_logger_name" in str(p) for p in processors)
        assert any("add_log_level" in str(p) for p in processors)

        # FileHandler setup
        log_dir = full_config["logger"]["log_directory"]
        file_name = full_config["file_handler"]["file_name"]
        file_path = tmp_path / log_dir / file_name

        d["mock_file_handler_class"].assert_called_once_with(file_path, mode="a", encoding="utf-8")
        d["mock_file_handler_instance"].setFormatter.assert_called_once_with(d["mock_processor_formatter_instance"])

        # RotatingFileHandler setup
        limited_file_name = full_config["limited_file_handler"]["file_name"]
        expected_limited_path = tmp_path / log_dir / limited_file_name
        d["mock_rotating_file_handler_class"].assert_called_once_with(
            expected_limited_path,
            maxBytes=full_config["limited_file_handler"]["max_bytes"],
            backupCount=full_config["limited_file_handler"]["backup_count"],
            encoding="utf-8",
        )
        d["mock_rotating_file_handler_instance"].setFormatter.assert_called_once_with(
            d["mock_processor_formatter_instance"]
        )

        # --- StreamHandler should be called, because it's enabled with the init method ---
        d["mock_stream_handler_class"].assert_called()

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_init_success_with_disabled_console_logging(
        self,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Test LoggingManager setup using a provided SettingsManager instance.
        """
        # Structlog mocks
        mock_get_logger = mock_structlog["get_logger"]
        mock_configure = mock_structlog["configure"]

        # LoggingManager dependencies
        d = mock_logging_manager_dependencies
        mock_translation = d["mock_translation_manager_instance"]
        mock_translation_singleton = d["mock_translation_manager_singleton_cls"]

        # Instantiate LoggingManager
        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(
                config=mock_settings_manager_instance,
                cli_log_level=logging.DEBUG,
            )
        # Verify translation setup
        mock_translation_singleton.get_instance.assert_called_once()
        mock_translation.gettext.assert_called()

        # Base assertions
        assert manager.cli_log_level == logging.DEBUG
        assert manager.enable_console_logging is False
        assert manager.setup_errors == []
        assert manager.logger is mock_get_logger.return_value
        mock_get_logger.assert_called_once_with("checkconnect.config.logging_manager")

        # Configure from settings
        full_config = mock_settings_manager_instance.get_full_config.return_value
        manager.configure_from_settings(full_config, logger_factory=d["mock_logger_factory_class"])

        # structlog.configure() called with correct arguments
        mock_configure.assert_called_once()
        config_kwargs = mock_configure.call_args or {}
        assert config_kwargs["cache_logger_on_first_use"] is True
        assert config_kwargs["logger_factory"] is d["mock_logger_factory_class"].return_value
        d["mock_logger_factory_class"].assert_called_once()

        processors = config_kwargs.get("processors", [])
        assert any(callable(p) for p in processors)
        assert any("add_logger_name" in str(p) for p in processors)
        assert any("add_log_level" in str(p) for p in processors)

        # FileHandler setup
        log_dir = full_config["logger"]["log_directory"]
        file_name = full_config["file_handler"]["file_name"]
        file_path = tmp_path / log_dir / file_name

        d["mock_file_handler_class"].assert_called_once_with(file_path, mode="a", encoding="utf-8")
        d["mock_file_handler_instance"].setFormatter.assert_called_once_with(d["mock_processor_formatter_instance"])

        # RotatingFileHandler setup
        limited_file_name = full_config["limited_file_handler"]["file_name"]
        expected_limited_path = tmp_path / log_dir / limited_file_name
        d["mock_rotating_file_handler_class"].assert_called_once_with(
            expected_limited_path,
            maxBytes=full_config["limited_file_handler"]["max_bytes"],
            backupCount=full_config["limited_file_handler"]["backup_count"],
            encoding="utf-8",
        )
        d["mock_rotating_file_handler_instance"].setFormatter.assert_called_once_with(
            d["mock_processor_formatter_instance"]
        )

        # --- StreamHandler should be called, because it's enabled with the init method ---
        d["mock_stream_handler_class"].assert_not_called()

    @pytest.mark.unit
    def test_structlog_output_with_processors_and_caplog(
        self,
        caplog: pytest.LogCaptureFixture,
        tmp_path: Path,
    ) -> None:
        """
        Integration-style test that verifies structured log output with structlog processors.
        """
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "logger": {
                "level": "DEBUG",
                "log_directory": str(log_dir),
            },
            "file_handler": {
                "enabled": False,
            },
            "limited_file_handler": {
                "enabled": False,
            },
            "console_handler": {
                "enabled": True,
            },
        }

        # Set caplog to DEBUG to capture structlog output
        with caplog.at_level(logging.DEBUG):
            manager = LoggingManager(config=config, enable_console_logging=True)
            logger = manager.logger

            # Log a message with some context
            logger.info("User login", user="alice", status="success")

        # Inspect log output captured by caplog
        assert any("User login" in msg for msg in caplog.messages)
        assert any(
            ("user" in msg and "alice" in msg) or ("status" in msg and "success" in msg) for msg in caplog.messages
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_init_raises_value_error_for_invalid_log_level(
        self,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
    ) -> None:
        """
        Test LoggingManager raises ValueError if an invalid log level is provided in settings.

        This test verifies that if the 'logger' section's 'level' setting is not
        a recognized logging level string, a ValueError is raised upon initialization.
        """
        # Simulate SettingsManager sections with an invalid log level
        bad_config = {
            "logger": {"level": "INVALID_LEVEL"},
            "file_handler": {"enabled": False},
            "limited_file_handler": {"enabled": False},
            "console_handler": {"enabled": False},
        }

        # Structlog mocks
        mock_get_logger = mock_structlog["get_logger"]
        mock_configure = mock_structlog["configure"]

        # LoggingManager dependencies
        d = mock_logging_manager_dependencies
        mock_translation = d["mock_translation_manager_instance"]
        mock_translation_singleton = d["mock_translation_manager_singleton_cls"]

        # Instantiate LoggingManager
        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(
                config=mock_settings_manager_instance,
            )

        manager.configure_from_settings(bad_config, logger_factory=d["mock_logger_factory_class"])

        assert any(error.startswith("Invalid log level") for error in manager.setup_errors)

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_log_directory_creation_failure(
        self,
        mocker: Any,
        mock_settings_manager_instance: MagicMock,
    ) -> None:
        """
        Ensure LoggingManager records setup error when log directory creation fails.

        This simulates Path.mkdir raising OSError during file handler setup,
        which LoggingManager should catch and log as a setup error.
        """
        # Arrange config
        config = {
            "logger": {"level": "INFO", "log_directory": "/fake/log/dir"},
            "file_handler": {"enabled": True, "file_name": "checkconnect.log"},
            "limited_file_handler": {"enabled": False},
        }

        # Patch the mkdir method of the parent directory to raise an error
        with patch("checkconnect.config.logging_manager.Path") as mock_path:
            mock_dir = mocker.MagicMock(spec=Path)
            mock_file = mocker.MagicMock(spec=Path)

            # `Path(log_dir_str)` -> mock_dir
            mock_path.return_value = mock_dir
            # `log_dir / file_name` -> mock_file
            mock_dir.__truediv__.return_value = mock_file
            # `mock_file.parent.mkdir()` -> raises error
            mock_file.parent.mkdir.side_effect = OSError("Permission denied")

            manager = LoggingManager(config=mock_settings_manager_instance)

            # Act
            manager.configure_from_settings(config)

            # Assert
            assert any("Failed to set up file handler" in msg for msg in manager.setup_errors)

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_ensure_log_dir_success_new_dir(
        self,
        mocker: Any,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Test _ensure_log_dir creates a new directory successfully.
        """
        log_dir = tmp_path / "log-directory"
        # Arrange config
        config = {
            "logger": {"level": "INFO", "log_directory": log_dir},
            "console_handler": {"enabled": True},
            "file_handler": {"enabled": True, "file_name": "checkconnect.log"},
            "limited_file_handler": {"enabled": False},
        }

        # Structlog mocks
        mock_get_logger = mock_structlog["get_logger"]
        mock_configure = mock_structlog["configure"]

        # LoggingManager dependencies
        d = mock_logging_manager_dependencies
        mock_translation = d["mock_translation_manager_instance"]
        mock_translation_singleton = d["mock_translation_manager_singleton_cls"]

        # Instantiate LoggingManager
        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(
                config=mock_settings_manager_instance,
            )

        manager.configure_from_settings(config, logger_factory=d["mock_logger_factory_class"])

        # Assert
        assert not manager.setup_errors
        assert log_dir.exists() == True

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_ensure_log_dir_success_existing_dir(
        self,
        mocker: Any,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Test _ensure_log_dir handles an already existing directory.
        """
        log_dir = tmp_path / "log-directory"
        log_dir.mkdir(parents=True, exist_ok=True)
        assert log_dir.exists() == True

        # Arrange config
        config = {
            "logger": {"level": "INFO", "log_directory": log_dir},
            "console_handler": {"enabled": True},
            "file_handler": {"enabled": True, "file_name": "checkconnect.log"},
            "limited_file_handler": {"enabled": False},
        }

        # Structlog mocks
        mock_get_logger = mock_structlog["get_logger"]
        mock_configure = mock_structlog["configure"]

        # LoggingManager dependencies
        d = mock_logging_manager_dependencies
        mock_translation = d["mock_translation_manager_instance"]
        mock_translation_singleton = d["mock_translation_manager_singleton_cls"]

        # Instantiate LoggingManager
        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(
                config=mock_settings_manager_instance,
            )

        manager.configure_from_settings(config, logger_factory=d["mock_logger_factory_class"])

        # Assert
        assert not manager.setup_errors
        assert log_dir.exists() == True

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_log_dir_not_specified_error(
        self,
        mocker: Any,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Test LoggingManager raises LogDirectoryError if the log directory cannot be created.
        """
        log_dir = ""

        # Arrange config
        config = {
            "logger": {"level": "INFO", "log_directory": log_dir},
            "console_handler": {"enabled": True},
            "file_handler": {"enabled": True, "file_name": "checkconnect.log"},
            "limited_file_handler": {"enabled": False},
        }

        # Structlog mocks
        mock_get_logger = mock_structlog["get_logger"]
        mock_configure = mock_structlog["configure"]

        # LoggingManager dependencies
        d = mock_logging_manager_dependencies
        mock_translation = d["mock_translation_manager_instance"]
        mock_translation_singleton = d["mock_translation_manager_singleton_cls"]

        # Instantiate LoggingManager
        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(
                config=mock_settings_manager_instance,
            )

        manager.configure_from_settings(config, logger_factory=d["mock_logger_factory_class"])

        # Assert
        assert manager.setup_errors
        # Assert
        assert any(
            "Failed to set up file handler: Log directory not specified in settings for file handler." in msg
            for msg in manager.setup_errors
        )


class TestLoggingManagerHandler:
    @pytest.mark.unit
    def test_file_handler_uses_processor_formatter(
        self,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ):
        """
        Ensure the file handler uses ProcessorFormatter and assigns it via setFormatter.
        """
        d = mock_logging_manager_dependencies
        mock_get_logger = mock_structlog["get_logger"]

        config = {
            "logger": {"level": "INFO", "log_directory": str(tmp_path)},
            "file_handler": {"enabled": True, "file_name": "app.log"},
            "limited_file_handler": {"enabled": False},
        }

        with patch("checkconnect.config.logging_manager.structlog.get_logger", new=mock_get_logger):
            manager = LoggingManager(config=mock_settings_manager_instance)
            manager.configure_from_settings(config)

        d["mock_file_handler_instance"].setFormatter.assert_called_once_with(d["mock_processor_formatter_instance"])

    @pytest.mark.unit
    def test_formatter_creation_failure_logs_error(
        self,
        mock_settings_manager_instance: MagicMock,
        mock_logging_manager_dependencies: dict[str, MagicMock],
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Simulates ProcessorFormatter raising an error and asserts LoggingManager handles it.
        """
        d = mock_logging_manager_dependencies
        logger_mock = MagicMock(name="structlog_logger")
        formatter_exception = Exception("Formatter init failed")

        config = {
            "logger": {"level": "INFO", "log_directory": str(tmp_path)},
            "file_handler": {"enabled": True, "file_name": "broken.log"},
            "limited_file_handler": {"enabled": False},
        }

        # Patch structlog.get_logger to return our logger_mock
        with patch("checkconnect.config.logging_manager.structlog.get_logger", return_value=logger_mock):
            d["mock_processor_formatter_class"].side_effect = formatter_exception

            manager = LoggingManager(config=mock_settings_manager_instance)
            manager.configure_from_settings(config)

        # Ensure the setup_errors list contains our message
        assert any("Formatter init failed" in msg for msg in manager.setup_errors)

        # Assert logger.error was called with expected args
        logger_mock.error.assert_any_call("Failed to set up file handler.", error=str(formatter_exception))

    @pytest.mark.unit
    def test_logging_output_with_caplog(
        self,
        caplog: pytest.LogCaptureFixture,
        mock_settings_manager_instance: MagicMock,
        mock_structlog: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Use caplog to verify a message was logged to the configured logger.
        """
        config = {
            "logger": {"level": "DEBUG", "log_directory": str(tmp_path)},
            "file_handler": {"enabled": False},
            "limited_file_handler": {"enabled": False},
        }

        # Do not patch getLogger to let caplog work
        manager = LoggingManager(config=mock_settings_manager_instance, enable_console_logging=True)

        with caplog.at_level(logging.DEBUG):
            logging.getLogger("checkconnect.config.logging_manager").debug("Hello from caplog")

        assert any("Hello from caplog" in msg for msg in caplog.messages)


class TestLoggingManagerContextManager:  # Changed class name for clarity
    @pytest.mark.unit
    def test_context_manager_enter(self, mock_settings_manager_instance: MagicMock) -> None:
        """
        Test the __enter__ method of the context manager.
        """
        mock_settings_manager_instance.get_section.side_effect = lambda section: {
            "logger": {"level": "INFO"},
            "file_handler": {"enabled": False},
            "limited_file_handler": {"enabled": False},
        }.get(section, {})

        manager = LoggingManager(config=mock_settings_manager_instance)
        with manager as ctx_manager:
            assert ctx_manager is manager

    @pytest.mark.unit
    def test_context_manager_exit_calls_shutdown(
        self,
        mock_settings_manager_instance: MagicMock,
        mocker: Any,
    ) -> None:
        """
        Test the __exit__ method of the LoggingManager context manager,
        ensuring LoggingManager.shutdown is called upon exiting the 'with' block.
        """

        # Patch the shutdown method on the class BEFORE the instance is created
        # so that when __exit__ calls shutdown, it calls our mock.
        mock_shutdown = mocker.patch.object(LoggingManager, "shutdown")
        mock_settings_manager_instance.get_section.side_effect = lambda section: {
            "logger": {"level": "INFO"},
            "file_handler": {"enabled": False},
            "limited_file_handler": {"enabled": False},
        }.get(section, {})

        # Create an instance and use it as a context manager
        # The __enter__ method will be called implicitly on entry.
        # The __exit__ method will be called implicitly on exit.
        with LoggingManager(config=mock_settings_manager_instance) as lm:
            # Inside the 'with' block, LoggingManager is active.
            # You could add assertions here if __enter__ has specific side effects you want to check.
            assert isinstance(lm, LoggingManager)  # Verify we got an instance
            mock_shutdown.assert_not_called()  # Shutdown should not be called yet

        # After the 'with' block, __exit__ should have been called,
        # which in turn should have called LoggingManager.shutdown().
        mock_shutdown.assert_called_once()

        # You might also want to ensure the singleton instance is cleaned up if shutdown does that
        # (though cleanup_singletons fixture might handle this).
        # assert LoggingManagerSingleton._instance is None
        #


class TestLoggingManagerSingleton:
    """
    Test suite for the LoggingManagerSingleton class.
    """

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_instance_creates_and_returns_single_instance(
        self,
    ) -> None:
        """
        Test get_instance creates a new instance on first call and returns the same on subsequent calls.
        """
        first_instance = LoggingManagerSingleton.get_instance()
        second_instance = LoggingManagerSingleton.get_instance()

        assert first_instance is second_instance
        # Verify that LoggingManager was initialized only once
        # This is implicitly tested by the autouse fixture resetting logging
        # and structlog, ensuring a fresh start for each test.
        # We can't directly count LoggingManager.__init__ calls due to mocking.
        # However, the singleton pattern's core is tested by `is` check.

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_clears_instance(self) -> None:
        """
        Test that reset sets the _instance to None.
        """
        # Ensure an instance exists
        instance = LoggingManagerSingleton.get_instance()
        assert instance is not None

        # Call the reset method
        LoggingManagerSingleton.reset()

        # Assert that the instance is now None
        assert LoggingManagerSingleton._instance is None  # noqa: SLF001

    @pytest.mark.unit
    @patch("checkconnect.config.logging_manager.LoggingManager")
    def test_reset_and_new_instance(self, mock_logging_manager_cls: MagicMock) -> None:
        """
        Test reset method clears the singleton instance and a new LoggingManager is created.
        """
        mock_instance_1 = MagicMock(name="FirstLoggingManager")
        mock_instance_2 = MagicMock(name="SecondLoggingManager")

        # Ensure each call to LoggingManager() gives a new instance
        mock_logging_manager_cls.side_effect = [mock_instance_1, mock_instance_2]

        # First singleton instance
        first_instance = LoggingManagerSingleton.get_instance()
        assert first_instance is mock_instance_1

        # Reset and get new instance
        LoggingManagerSingleton.reset()
        second_instance = LoggingManagerSingleton.get_instance()
        assert second_instance is mock_instance_2

        # ✅ Main assertion
        assert first_instance is not second_instance

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_calls_instance_shutdown(self) -> None:
        """
        Test that reset calls the shutdown method of the contained instance.
        """
        # We need to mock the LoggingManager's shutdown method before creating an instance
        # so we can track its calls.
        with patch.object(LoggingManager, "shutdown") as mock_instance_shutdown:
            instance = LoggingManagerSingleton.get_instance()
            assert instance is not None  # Ensure an instance was created

            # Call the reset method
            LoggingManagerSingleton.reset()

            # Assert that the instance's shutdown method was called exactly once
            mock_instance_shutdown.assert_called_once()

        # Additionally, verify the singleton's _instance is now None
        assert LoggingManagerSingleton._instance is None  # noqa: SLF001

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_initialization_errors(
        self,
    ) -> None:
        """
        Test get_initialization_errors method returns errors during initialization.
        """
        # We need to patch __init__ BEFORE the singleton tries to create an instance.
        # This means patching it within a 'with' statement, and then calling get_instance
        # inside that 'with' statement.

        # The key is that cleanup_singletons should ensure LoggingManagerSingleton
        # is reset, so get_instance() will call __init__ again.
        with (
            patch.object(LoggingManager, "__init__", side_effect=Exception("Mocked error")),
            pytest.raises(Exception, match="Mocked error"),
        ):
            # Call get_instance *inside* the patch context.
            # This will trigger __init__ with the side_effect.
            LoggingManagerSingleton.get_instance()

        # After the exception is caught, you could potentially assert on the instance's errors
        # if the LoggingManager's __init__ was designed to set them even on failure.
        # However, since the Exception propagates, the instance won't be fully initialized.
        # This test primarily validates the exception propagation.

        # If you *also* need to check self.setup_errors, you'd need to catch the exception,
        # and then inspect the *exception object itself* if it contained the instance,
        # or mock the append method to capture what would have been appended.
        # For now, let's focus on the primary failure (exception not raised).

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_clears_initialization_errors(self) -> None:
        """
        Test that reset clears any accumulated initialization errors.
        """
        # Manually add an error to simulate a previous failed initialization
        LoggingManagerSingleton._initialization_errors.append("Simulated init error 1")  # noqa: SLF001
        LoggingManagerSingleton._initialization_errors.append("Simulated init error 2")  # noqa: SLF001

        # Verify errors are present before reset
        assert len(LoggingManagerSingleton.get_initialization_errors()) == 2

        # Call the reset method
        LoggingManagerSingleton.reset()

        # Assert that the errors list is now empty
        assert LoggingManagerSingleton.get_initialization_errors() == []
        assert len(LoggingManagerSingleton.get_initialization_errors()) == 0

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_initialization_errors_returns_correct_errors(self) -> None:
        """
        Test get_initialization_errors returns errors during initialization.
        This re-uses the pattern from your previous test problem.
        """
        # Patch LoggingManager's __init__ to raise an error
        expected_error_msg = "Mocked init error for test"
        with patch.object(LoggingManager, "__init__", side_effect=Exception(expected_error_msg)):
            with pytest.raises(Exception, match=expected_error_msg):
                # This call will trigger __init__ which will raise the error
                LoggingManagerSingleton.get_instance()

            # Now, after the exception, check if the error was logged in the singleton
            errors = LoggingManagerSingleton.get_initialization_errors()
            assert len(errors) == 1
            assert expected_error_msg in errors[0]  # Check that the message is part of the error string

        # Ensure cleanup_singletons runs after this test to clear the error for subsequent tests
