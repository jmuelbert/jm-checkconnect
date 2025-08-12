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

from checkconnect.cli import main as cli_main
from checkconnect.config.appcontext import AppContext
from checkconnect.exceptions import ExitExceptionError
from tests.utils.common import assert_common_cli_logs, assert_common_initialization, clean_cli_output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    # If EventDict is a specific type alias in structlog
    from structlog.typing import EventDict
    from typer.testing import CliRunner


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

        # Act
        result = runner.invoke(
            cli_main.main_app,
            [
                "gui",
            ],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )


        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=False,
        )

        # Specific assertion for the GUI command
        mock_gui_startup_run.assert_called_once_with(
            context=app_context_instance,  # Use the direct instance for clarity
            language=None,  # As no --language argument was passed
        )

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
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

        # Act
        result = runner.invoke(
            cli_main.main_app,
            [
                cli_arg,
                language_value,
                "gui",
            ],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Unexpected failure: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,
            expected_language=expected_language_for_translation,  # Use the specific expected language
            expected_console_logging=False,
        )

        # Specific assertion for the GUI command
        mock_gui_startup_run.assert_called_once_with(
            context=app_context_instance,
            language=expected_gui_language_arg,  # Use the specific expected language for the GUI startup
        )

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is language_value
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
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

        result = runner.invoke(
            cli_main.main_app,
            ["gui"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        assert result.exit_code == 1, f"Missing exception: {result.output}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=False,
        )

        # Assert GUI failure message in stdout
        assert "Cannot start GUI due to application error:" in cleaned, (
            "Expected 'Cannot start GUI due to application error:' in stdout"
        )
        assert "GUI failure" in cleaned, "Expected 'GUI failure' in stdout"

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
        )

        assert any(
            "exc_info" in e
            and e.get("event") == "Cannot start GUI due to application error."
            and isinstance(e.get("exc_info"), ExitExceptionError)
            and str(e.get("exc_info")) == "GUI failure"
            and e.get("log_level") == "error"
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

        result = runner.invoke(
            cli_main.main_app,
            ["gui"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "An unexpected error occurred during GUI startup:" in cleaned, (
            "Expected 'An unexpected error occurred during GUI startup:'"
        )
        assert "Crash" in cleaned, "Expected 'Crash'"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=False,
        )

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # 3. Assert GUI specific startup INFO log
        assert any(
            e.get("event") == "Starting CheckConnect GUI..." and e.get("log_level") == "info" for e in caplog_structlog
        )

        assert any(
            "exc_info" in e
            and e.get("event") == "An unexpected error occurred during GUI startup."
            and isinstance(e.get("exc_info"), RuntimeError)
            and str(e.get("exc_info")) == "Crash"
            and e.get("log_level") == "error"
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

        result = runner.invoke(
            cli_main.main_app,
            ["gui", "--help"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert
        assert result.exit_code == 0, f"Unexpected failure: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=False,
        )

        # Headers
        assert "Usage: cli gui [OPTIONS]" in cleaned
        assert "Run CheckConnect in graphical user interface (GUI) mode." in cleaned
        # Options
        assert "--help Show this message and exit." in cleaned
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
