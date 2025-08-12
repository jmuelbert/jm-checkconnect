# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Tests for the Report subcommand in Typer main_app (as a submodule).

This ensures the main_app correctly routes to the Report command, initializes
AppContext, and calls startup.run with the right context.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

# Import the report_app Typer instance and the command function
# Adjust this import path if your file structure is different
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


@pytest.fixture
def mock_report_manager_class():
    """Mocks the ReportManager class and its instance methods."""
    with patch("checkconnect.cli.report_app.ReportManager") as mock_rm_class:
        mock_instance = MagicMock(name="ReportManager_instance")
        mock_instance.load_previous_results.return_value = (["mocked_ntp_data"], ["mocked_url_data"])
        mock_instance.results_exists.return_value = False
        mock_rm_class.from_params.return_value = mock_instance
        yield mock_rm_class


@pytest.fixture
def mock_report_generator_class():
    """Mocks the ReportGenerator class and its instance methods."""
    with patch("checkconnect.cli.report_app.ReportGenerator") as mock_rg_class:
        mock_instance = MagicMock(name="ReportGenerator_instance")
        mock_instance.generate_reports.return_value = None
        mock_rg_class.from_params.return_value = mock_instance
        yield mock_rg_class


@pytest.fixture
def mock_checkconnect_class(mocker: MockerFixture):
    """
    Mocks the CheckConnect class and its instance methods, including getters.

    This version correctly mocks properties using PropertyMock.
    """
    with patch("checkconnect.cli.report_app.CheckConnect") as mock_cc_class:
        # Create a mock instance of the CheckConnect class.
        mock_instance = MagicMock(name="CheckConnect_instance")
        mock_instance.run_all_checks.return_value = None

        # Correctly mock the getter properties for ntp_results and url_results.
        # We use PropertyMock to set the return value for when the property is accessed.
        # This is the crucial change.
        mocker.patch.object(
            mock_instance, "ntp_results", new_callable=PropertyMock(return_value=["mocked_ntp_data_from_getter"])
        )
        mocker.patch.object(
            mock_instance, "url_results", new_callable=PropertyMock(return_value=["mocked_url_data_from_getter"])
        )

        # Set the mock class to return our mock instance when called.
        mock_cc_class.return_value = mock_instance
        yield mock_cc_class


class TestCliReports:
    @pytest.mark.integration
    def test_report_command_from_main_runs_successfully(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        mock_report_generator_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Ensure run_command completes successfully when ReportManager runs without error.
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

        mock_report_manager_instance = mock_report_manager_class.from_params.return_value
        mock_report_manager_instance.results_exists.return_value = True  # <-- WICHTIG: Überschreibe hier!

        result = runner.invoke(
            cli_main.main_app,
            ["report"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"
        assert "Reports generated successfully" in cleaned

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertion for the report command
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_called_once_with()

        mock_report_generator_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_reports_dir=None
        )
        # Assert ReportGenerator instance's generate_reports was called with the loaded data
        mock_report_generator_class.from_params.return_value.generate_reports.assert_called_once_with(
            ntp_results=["mocked_ntp_data"],
            url_results=["mocked_url_data"],
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

        # 3. Assert report specific startup INFO log
        assert any(
            e.get("event") == "Starting Checkconnect in generate-reports mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_reports_generates_from_existing_results(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        mock_report_generator_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test successful report generation when previous results exist.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        mock_report_manager_instance = mock_report_manager_class.from_params.return_value
        mock_report_manager_instance.results_exists.return_value = True  # <-- WICHTIG: Überschreibe hier!

        data_dir_path = Path("/mock/data")
        reports_dir_path = Path("/mock/reports")

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            [
                "report",
                "--reports-dir",
                str(reports_dir_path),
                "--data-dir",
                str(data_dir_path),
            ],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"
        assert "Reports generated successfully" in cleaned

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertion for the report command
        mock_report_manager_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_data_dir=data_dir_path
        )
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once()
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_called_once_with()

        mock_report_generator_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_reports_dir=reports_dir_path
        )
        # Assert ReportGenerator instance's generate_reports was called with the loaded data
        mock_report_generator_class.from_params.return_value.generate_reports.assert_called_once_with(
            ntp_results=["mocked_ntp_data"],
            url_results=["mocked_url_data"],
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

        # 3. Assert report specific startup INFO log
        assert any(
            e.get("event") == "Starting Checkconnect in generate-reports mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_reports_command_success_without_existing_results(
        self,
        mock_dependencies: dict[str, Any],
        mock_checkconnect_class: MagicMock,
        mock_report_manager_class: MagicMock,
        mock_report_generator_class: MagicMock,
        tmp_path: Path,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test successful report generation when no previous results exist,
        triggering new checks.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]
        checkconnect_instance = mock_dependencies["check_connect_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        # Configure ReportManager to indicate results exist
        mock_report_manager_class.from_params.return_value.results_exists.return_value = False
        # The load_previous_results return value is already set in the fixture

        # Define paths for options
        reports_dir = tmp_path / "my_reports_new"
        data_dir = tmp_path / "my_data_new"
        config_file = tmp_path / "config.toml"
        config_file.touch()  # Create dummy config file

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            [
                "--config",
                str(config_file),
                "report",
                "--reports-dir",
                str(reports_dir),
                "--data-dir",
                str(data_dir),
            ],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"
        assert "Reports generated successfully" in cleaned

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Check first for existing results
        # Verify ReportManager.from_params was called (even if no existing results)
        mock_report_manager_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_data_dir=data_dir
        )
        mock_report_manager_instance = mock_report_manager_class.from_params.return_value
        mock_report_manager_instance.results_exists.assert_called_once()
        mock_report_manager_instance.load_previous_results.assert_not_called()  # Should not be called

        # If result doesn't exists generate new results
        mock_checkconnect_class.assert_called_once_with(context=AppContext.create.return_value)
        checkconnect_instance = mock_checkconnect_class.return_value
        checkconnect_instance.run_all_checks.assert_called_once()

        # Finally generate the reports in HTML and PDF formats
        # Verify ReportGenerator.from_params and generate_reports were called with new results
        mock_report_generator_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_reports_dir=reports_dir
        )
        mock_report_generator_instance = mock_report_generator_class.from_params.return_value
        mock_report_generator_instance.generate_reports.assert_called_once_with(
            ntp_results=["mocked_ntp_data_from_getter"], url_results=["mocked_url_data_from_getter"]
        )

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") == str(config_file)
            for e in caplog_structlog
        )

        # 3. Assert report specific startup INFO log
        assert any(
            e.get("event") == "Starting Checkconnect in generate-reports mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_reports_command_default_paths(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        mock_report_generator_class: MagicMock,
        mock_checkconnect_class: MagicMock,
        tmp_path: Path,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that the command works correctly without explicitly providing
        reports_dir and data_dir, relying on default option definitions.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        # Configure ReportManager to indicate results exist
        mock_report_manager_class.from_params.return_value.results_exists.return_value = False
        # The load_previous_results return value is already set in the fixture
        mock_report_manager_class.load_previous_results.return_value = ([], [])

        config_file = tmp_path / "config.toml"
        config_file.touch()

        # Invoke the command without --reports-dir or --data-dir
        result = runner.invoke(
            cli_main.main_app,
            ["--config", str(config_file), "report"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"
        assert "Reports generated successfully" in cleaned

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # If result doesn't exists generate new results
        mock_checkconnect_class.assert_called_once_with(context=AppContext.create.return_value)
        checkconnect_instance = mock_checkconnect_class.return_value
        checkconnect_instance.run_all_checks.assert_called_once()

        # Verify ReportManager.from_params and ReportGenerator.from_params
        # were called. The actual default paths would depend on get_data_dir_option_definition
        # and get_report_dir_option_definition, which are usually dynamic (e.g., based on XDG).
        # For this test, we just check they were called. The specific path values
        # would need more complex mocking if we want to assert the *exact* default paths.
        # However, since they are 'None' in the function signature, we'd expect them
        # to be resolved by the respective `get_..._option_definition()` functions
        # before being passed to `from_params`. This test asserts the flow.
        # Specific assertion for the report command
        mock_report_manager_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_data_dir=None
        )
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once()

        mock_report_generator_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_reports_dir=None
        )

        # Assert ReportGenerator instance's generate_reports was called with the loaded data
        mock_report_generator_class.from_params.return_value.generate_reports.assert_called_once_with(
            ntp_results=["mocked_ntp_data_from_getter"],
            url_results=["mocked_url_data_from_getter"],
        )

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") is None
            and e.get("config_file") == str(config_file)
            for e in caplog_structlog
        )

        # 3. Assert report specific startup INFO log
        assert any(
            e.get("event") == "Starting Checkconnect in generate-reports mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_reports_command_exit_exception_error(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_generator_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test error handling when an ExitExceptionError occurs.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        # Setup mocks to raise ExitExceptionError
        mock_report_generator_class.from_params.side_effect = ExitExceptionError("Test error")

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            ["report"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert CLI command exits with code 0
        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "Cannot start generate reports for checkconnect." in cleaned, (
            "Expected 'Cannot start generate reports for checkconnect.' in stdout"
        )
        assert "Test error" in cleaned, "Expected 'Test error' in stdout"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertion for the report command
        mock_report_generator_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_reports_dir=None
        )
        # Ensure generate_reports was not called as an error occurred early
        mock_report_generator_class.from_params.return_value.generate_reports.assert_not_called()

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

        # Assert ERROR/CRITICAL logs
        assert any(
            "exc_info" in e
            and e.get("event") == "Cannot start generate reports for checkconnect error."
            and isinstance(e.get("exc_info"), ExitExceptionError)
            and str(e.get("exc_info")) == "Test error"
            and e.get("log_level") == "error"
            for e in caplog_structlog
        )

    @pytest.mark.integration
    def test_reports_command_handles_unexpected_exception(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        mock_report_generator_class: MagicMock,
        mock_checkconnect_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test error handling when an ExitExceptionError occurs.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        checkconnect_instance = mock_checkconnect_class.return_value
        checkconnect_instance.run_all_checks.side_effect = RuntimeError("Something went wrong")

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            ["report"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Assert CLI command exits with code 0
        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "An unexpected error occurred generate reports." in cleaned, (
            "Expected 'An unexpected error occurred generate reports.' in stdout"
        )
        assert "Something went wrong" in cleaned, "Expected 'Test error' in stdout"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance=settings_manager_instance,
            logging_manager_instance=logging_manager_instance,
            translation_manager_instance=translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertion for the report command
        mock_report_manager_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_data_dir=None
        )
        # Ensure generate_reports was not called as an error occurred early
        mock_report_generator_class.from_params.return_value.generate_reports.assert_not_called()

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

        # Assert ERROR/CRITICAL logs
        assert any(
            "exc_info" in e
            and e.get("event") == "An unexpected error occurred generate reports."
            and isinstance(e.get("exc_info"), RuntimeError)
            and str(e.get("exc_info")) == "Something went wrong"
            and e.get("log_level") == "error"
            for e in caplog_structlog
        )

    def test_report_command_with_help_option(
        self,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that 'run summary --help' displays the help message specific to the 'run' command.
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
            ["report", "--help"],
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
        )

        # Headers
        assert "Usage: cli report [OPTIONS]" in cleaned
        assert " Generate HTML and PDF reports from the most recent connectivity test results." in result.output
        # Options
        assert "--help Show this message and exit." in cleaned
        # Configuration
        assert (
            "--data-dir -d DIRECTORY Directory where data will be saved. Default used the system defined user data dir. [default: None]"
            in cleaned
        )
        assert (
            "-reports-dir -r DIRECTORY Directory where reports will be saved (overrides config). [default: None]"
            in cleaned
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
