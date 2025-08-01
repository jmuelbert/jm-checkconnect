# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest


from checkconnect.cli import main as cli_main
from checkconnect.config.appcontext import AppContext
from checkconnect.exceptions import ExitExceptionError
from checkconnect.reports.report_manager import OutputFormat
from tests.utils.common import assert_common_cli_logs, assert_common_initialization

if TYPE_CHECKING:
    # If EventDict is a specific type alias in structlog
    from structlog.typing import EventDict
    from typer.testing import CliRunner
else:
    EventDict = dict[str, Any]


@pytest.fixture
def mock_report_manager_class():
    """Mocks the ReportManager class and its instance methods."""
    with patch("checkconnect.cli.summary_app.ReportManager") as mock_rm_class:
        mock_instance = MagicMock(name="ReportManager_instance")
        mock_instance.load_previous_results.return_value = (["mocked_ntp_data"], ["mocked_url_data"])
        mock_instance.results_exists.return_value = False
        mock_rm_class.from_params.return_value = mock_instance
        yield mock_rm_class


@pytest.fixture
def mock_checkconnect_class():
    """Mocks the CheckConnect class and its instance methods, including getters."""
    with patch("checkconnect.cli.summary_app.CheckConnect") as mock_cc_class:
        mock_instance = MagicMock(name="CheckConnect_instance")
        mock_instance.run_all_checks.return_value = None

        # NEU: Mock die Getter-Methoden anstatt der direkten Attribute
        mock_instance.get_ntp_results.return_value = ["mocked_ntp_data_from_getter"]
        mock_instance.get_url_results.return_value = ["mocked_url_data_from_getter"]

        mock_cc_class.return_value = mock_instance
        yield mock_cc_class


class TestCliSummary:
    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("cli_arg", "expected_format"),
        [
            ("text", OutputFormat.text.value),
            ("markdown", OutputFormat.markdown.value),
            ("html", OutputFormat.html.value),
        ],
    )
    def test_summary_command_runs_successfully(
        self,
        cli_arg: str,
        expected_format: OutputFormat,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that the summary subcommand initializes correctly and runs without error.
        Mocks `startup_summary` to prevent actually launching the summary.
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

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            cli_main.main_app,
            ["summary", "--format", cli_arg],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"
        assert "Results:" in result.output

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertions for summary mode
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.get_summary.assert_called_once_with(
            ntp_results=["mocked_ntp_data"], url_results=["mocked_url_data"], summary_format=expected_format
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
            e.get("event") == "Starting Checkconnect in summary mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_summary_command_default_paths(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
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
        mock_report_manager_class.from_params.return_value.results_exists.return_value = True

        config_file = tmp_path / "config.toml"
        config_file.touch()

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        # Invoke the command without --reports-dir or --data-dir
        result = runner.invoke(
            cli_main.main_app,
            ["--config", str(config_file), "summary"],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"
        assert "Results:" in result.output

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Verify ReportManager.from_params
        # Specific assertions for summary mode
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.get_summary.assert_called_once_with(
            ntp_results=["mocked_ntp_data"], url_results=["mocked_url_data"], summary_format=OutputFormat.text.value
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
            e.get("event") == "Starting Checkconnect in summary mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_summary_command_without_previous_results(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """Test the summary command without previous results."""
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
        mock_report_manager_instance.results_exists.return_value = False  # <-- WICHTIG: Überschreibe hier!

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            cli_main.main_app,
            ["summary"],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "No saved result found." in result.stdout, "Expected 'No saved result found.' in stdout"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertions for summary mode
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_not_called()
        mock_report_manager_class.from_params.return_value.get_summary.assert_not_called()
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
            e.get("event") == "Starting Checkconnect in summary mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_manager_command_exit_exception_error(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """Test that exceptions during summary startup are logged and handled."""
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
        mock_report_manager_class.from_params.side_effect = ExitExceptionError("Test error")

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            ["summary"],
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "Cannot start generate summary for checkconnect." in result.stdout, (
            "Expected 'Cannot start generate reports for checkconnect.' in stdout"
        )
        assert "Test error" in result.stdout, "Expected 'Test error' in stdout"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        # Specific assertion for the report command
        mock_report_manager_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, arg_data_dir=None
        )
        # Ensure generate_reports was not called as an error occurred early
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_not_called()

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
            e.get("event") == "Starting Checkconnect in summary mode." and e.get("log_level") == "info"
            for e in caplog_structlog
        )

        # Assert ERROR/CRITICAL logs
        assert any(
            "exc_info" in e
            and e.get("event") == "Cannot start generate summary for checkconnect."
            and isinstance(e.get("exc_info"), ExitExceptionError)
            and str(e.get("exc_info")) == "Test error"
            and e.get("log_level") == "error"
            for e in caplog_structlog
        )
        

    def test_cli_wrong_summary_format(
        self,
        mock_dependencies: dict[str, Any],
        mock_report_manager_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        # Configure ReportManager to indicate results exist
        mock_report_manager_class.from_params.return_value.results_exists.return_value = True

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        # Invoke the command without --reports-dir or --data-dir
        result = runner.invoke(
            cli_main.main_app,
            ["summary", "--format", "json"],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code != 0, f"Missing exception: {result.output}"
        assert (
            "Invalid value for '--format' / '-f': 'json' is not one of 'text', 'markdown', 'html'. " in result.stdout
        ), "Expected 'Invalid value for '--format' / '-f': 'json' is not one of 'text', 'markdown', 'html'. ' in stdout"

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

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(cli_main.main_app, ["summary", "--help"])

        # Assert
        assert result.exit_code == 0, f"Unexpected failure: {result.exception}"

        print(result.stdout)

        # Headers
        assert "Usage: cli summary [OPTIONS]" in result.output
        assert "Generate a summary of the most recent connectivity test results." in result.output
        # Options
        assert "--help          Show this message and exit." in result.output
        # Configuration
        assert (
            "--data-dir  -d      DIRECTORY             Directory where data will be saved. Default used the system defined user data dir. [default: None]"
            in result.output
        )
        assert (
            "-format    -f      [text|markdown|html]  Output format: text, markdown, html. [default: text]"
            in result.output
        )
