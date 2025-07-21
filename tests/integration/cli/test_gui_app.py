# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Tests for the GUI subcommand in Typer main_app (as a submodule).

This ensures the main_app correctly routes to the GUI command, initializes
AppContext, and calls startup.run with the right context.
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Any

import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock
from typer.testing import CliRunner

from checkconnect.cli import main as cli_main
import checkconnect.gui.startup as gui_startup  # For patching
from checkconnect.exceptions import ExitExceptionError
from checkconnect.config.appcontext import AppContext

from tests.utils.common import assert_common_initialization

if TYPE_CHECKING:
    # If EventDict is a specific type alias in structlog
    from structlog.typing import EventDict
else:
    EventDict = dict[str, Any]


class TestCliGUI:
    @pytest.mark.integration
    def test_gui_command_from_main_runs_successfully(
        self,
        mocker: MockerFixture,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that 'gui' subcommand runs without errors with default settings.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]  # You can use this for direct assertions

        # Ensure AppContext.create.return_value is readily available for later assertions
        # (It should be mock_dependencies["app_context_instance"])
        # mocker.patch.object(AppContext, "create", return_value=app_context_instance) # This patch should be in conftest
        # Verify it points to the correct mock if AppContext.create is mocked in conftest
        assert AppContext.create.return_value == app_context_instance

        mock_gui_startup_run = mocker.patch("checkconnect.cli.gui_app.startup.run", return_value=None)

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        # Act
        result = runner.invoke(
            cli_main.main_app,
            [
                "gui",
            ],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
        )

        # Specific assertion for the GUI command
        mock_gui_startup_run.assert_called_once_with(
            context=app_context_instance,  # Use the direct instance for clarity
            language=None,  # As no --language argument was passed
        )

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 2. Assert key INFO level success messages
        assert any(
            e.get("event") == "Main callback: SettingsManager initialized and configuration loaded."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: TranslationManager initialized." and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: Full logging configured based on application settings and CLI options."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
        )

        # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == 0
            and e.get("derived_cli_log_level") == "WARNING"
            for e in caplog_structlog
        )

        # 5. Assert "Debug logging is active" (DEBUG)
        # This one is tricky if it *always* appears when `caplog_structlog` captures at DEBUG.
        # If it specifically means the *application* is running in debug, then assert.
        # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # At the end of the assert block for successful tests:
        assert not any(e.get("log_level") == "error" or e.get("log_level") == "critical" for e in caplog_structlog), (
            "Unexpected ERROR or CRITICAL logs found in a successful test run."
        )

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("cli_arg", "language_value", "expected_language_for_translation", "expected_gui_language_arg"),
        [
            ("--language", "en", "en", "en"),
            ("-l", "de", "de", "de"),
            ("--language", "es", "es", "es"),
        ],
    )
    def test_gui_command_from_main_runs_with_languages(
        self,
        cli_arg: str,
        language_value: str,
        expected_language_for_translation: str,
        expected_gui_language_arg: str,
        mocker: MockerFixture,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that 'gui' subcommand runs with language arguments and sets them correctly.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        mock_gui_startup_run = mocker.patch("checkconnect.cli.gui_app.startup.run", return_value=None)

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        # Act
        result = runner.invoke(
            cli_main.main_app,
            [
                cli_arg,
                language_value,
                "gui",
            ],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Unexpected failure: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,
            expected_language=expected_language_for_translation,  # Use the specific expected language
        )

        # Specific assertion for the GUI command
        mock_gui_startup_run.assert_called_once_with(
            context=app_context_instance,
            language=expected_gui_language_arg,  # Use the specific expected language for the GUI startup
        )

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is language_value
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 2. Assert key INFO level success messages
        assert any(
            e.get("event") == "Main callback: SettingsManager initialized and configuration loaded."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: TranslationManager initialized." and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: Full logging configured based on application settings and CLI options."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
        )

        # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == 0
            and e.get("derived_cli_log_level") == "WARNING"
            for e in caplog_structlog
        )

        # 5. Assert "Debug logging is active" (DEBUG)
        # This one is tricky if it *always* appears when `caplog_structlog` captures at DEBUG.
        # If it specifically means the *application* is running in debug, then assert.
        # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # At the end of the assert block for successful tests:
        assert not any(e.get("log_level") == "error" or e.get("log_level") == "critical" for e in caplog_structlog), (
            "Unexpected ERROR or CRITICAL logs found in a successful test run."
        )

    @pytest.mark.integration
    def test_gui_command_handles_exit_exception_from_subcommand(
        self,
        mocker: MockerFixture,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that ExitExceptionError in startup.run causes a clean exit (exit code 1).
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        mocker.patch("checkconnect.cli.gui_app.startup.run", side_effect=ExitExceptionError("GUI failure"))

        result = runner.invoke(cli_main.main_app, ["gui"])

        assert result.exit_code == 1, f"Missing exception: {result.output}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
        )

        assert "GUI failure" in result.stdout

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 2. Assert key INFO level success messages
        assert any(
            e.get("event") == "Main callback: SettingsManager initialized and configuration loaded."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: TranslationManager initialized." and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: Full logging configured based on application settings and CLI options."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
        )

        # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == 0
            and e.get("derived_cli_log_level") == "WARNING"
            for e in caplog_structlog
        )

        # 5. Assert "Debug logging is active" (DEBUG)
        # This one is tricky if it *always* appears when `caplog_structlog` captures at DEBUG.
        # If it specifically means the *application* is running in debug, then assert.
        # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert any(
            e.get("event") == "Cannot start GUI due to application error: GUI failure"
            and e.get("log_level") in ["error", "critical"]
            for e in caplog_structlog
        )

    @pytest.mark.integration
    def test_gui_command_handles_unexpected_exception(
        self,
        mocker: MockerFixture,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that unexpected Exception in startup.run causes a clean exit (exit code 1).
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        mocker.patch("checkconnect.cli.gui_app.startup.run", side_effect=RuntimeError("Crash"))

        result = runner.invoke(cli_main.main_app, ["gui"])

        assert result.exit_code == 1, f"Missing exception: {result.output}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
        )

        assert "Crash" in result.stdout

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 2. Assert key INFO level success messages
        assert any(
            e.get("event") == "Main callback: SettingsManager initialized and configuration loaded."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: TranslationManager initialized." and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: Full logging configured based on application settings and CLI options."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
        )

        # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == 0
            and e.get("derived_cli_log_level") == "WARNING"
            for e in caplog_structlog
        )

        # 5. Assert "Debug logging is active" (DEBUG)
        # This one is tricky if it *always* appears when `caplog_structlog` captures at DEBUG.
        # If it specifically means the *application* is running in debug, then assert.
        # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert any(
            e.get("event") == "An unexpected error occurred during GUI startup: Crash"
            and e.get("log_level") in ["error", "critical"]
            for e in caplog_structlog
        )

    @pytest.mark.integration
    def test_gui_command_with_help_option(
        self,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that 'gui --help' displays the help message specific to the 'gui' command.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(cli_main.main_app, ["gui", "--help"], env=test_env)

        # Assert
        assert result.exit_code == 0, f"Unexpected failure: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
        )

        # Headers
        assert "Usage: cli gui [OPTIONS]" in result.output
        assert "Run CheckConnect in graphical user interface (GUI) mode." in result.output
        # Options
        assert "--help          Show this message and exit." in result.output
        # ---

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 2. Assert key INFO level success messages
        assert any(
            e.get("event") == "Main callback: SettingsManager initialized and configuration loaded."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: TranslationManager initialized." and e.get("log_level") == "info"
            for e in caplog_structlog
        )
        assert any(
            e.get("event") == "Main callback: Full logging configured based on application settings and CLI options."
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # 3. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == 0
            and e.get("derived_cli_log_level") == "WARNING"
            for e in caplog_structlog
        )

        # At the end of the assert block for successful tests:
        assert not any(e.get("log_level") == "error" or e.get("log_level") == "critical" for e in caplog_structlog), (
            "Unexpected ERROR or CRITICAL logs found in a successful test run."
        )
