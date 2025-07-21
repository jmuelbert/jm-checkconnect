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

import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import the report_app Typer instance and the command function
# Adjust this import path if your file structure is different
from checkconnect.cli import main as cli_main

from checkconnect.config.appcontext import AppContext
from checkconnect.exceptions import ExitExceptionError
from checkconnect.reports.report_generator import ReportGenerator
from checkconnect.reports.report_manager import ReportManager


@pytest.fixture
def mock_report_manager_class():
    """Mocks the ReportManager class and its instance methods."""
    with patch("checkconnect.cli.report_app.ReportManager") as mock_rm_class:
        mock_instance = MagicMock(name="ReportManager_instance")
        mock_instance.load_previous_results.return_value = (["mocked_ntp_data"], ["mocked_url_data"])
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


class TestCliReports:
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
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            cli_main.main_app,
            ["report"],
            env=test_env,
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # --- Assertions ---

        # SettingsManager
        settings_manager_instance.get_all_settings.assert_called_once()

        # Ensure get_section('logger') was called to retrieve logging config
        settings_manager_instance.get_section.assert_called_once_with("logger")

        # TranslationManager: Ensure configure was called
        translation_manager_instance.configure.assert_called_once_with(
            language="en",  # Assuming 'en' is the default from settings or hardcoded
            translation_domain=None,  # Assuming these are None by default
            locale_dir=None,
        )

        # AppContext: Ensure AppContext.create was called with the correct manager instances
        AppContext.create.assert_called_once_with(
            settings_instance=settings_manager_instance,
            translator_instance=translation_manager_instance,
        )

        # Logging Manager: Ensure apply_configuration was called
        # IMPORTANT: The log_config argument here should match what settings_manager_instance.get_section("logger") returns
        expected_log_config = settings_manager_instance.get_section.return_value  # Get the mocked return value
        logging_manager_instance.apply_configuration.assert_called_once_with(
            cli_log_level=logging.WARNING,  # As verbose=0 maps to WARNING in your VERBOSITY_LEVELS
            enable_console_logging=True,
            log_config=settings_manager_instance.get_section("logger"),
            translator=translation_manager_instance,
        )

        mock_report_manager_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, data_dir=None
        )

        # Assert ReportManager instance methods were called
        mock_report_manager_class.from_params.return_value.results_exists.assert_called_once_with()
        mock_report_manager_class.from_params.return_value.load_previous_results.assert_called_once_with()

        mock_report_generator_class.from_params.assert_called_once_with(
            context=AppContext.create.return_value, reports_dir=None
        )
        # Assert ReportGenerator instance's generate_reports was called with the loaded data
        mock_report_generator_class.from_params.return_value.generate_reports.assert_called_once_with(
            ntp_results=["mocked_ntp_data"],
            url_results=["mocked_url_data"],
        )
        assert "Translated: Error in generate-reports mode" not in result.stdout  # Ensure no error message

        # --- Asserting on Log Entries using caplog_structlog ---
        print("Asserting on Log Entries using caplog_structlog:")
        for log_entry in caplog_structlog:
            print(log_entry)
        print("------------------------------------------------")

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
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

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
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        # Arrange
        # Configure ReportManager to indicate results exist
        mock_report_manager_class.from_params.return_value.results_exists.return_value = True
        # The load_previous_results return value is already set in the fixture

        data_dir_path = Path("/mock/data")
        reports_dir_path = Path("/mock/reports")

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            [
                "--language",
                "en",
                "--verbose",
                "report",
                "--reports-dir",
                str(reports_dir_path),
                "--data-dir",
                str(data_dir_path),
            ],
        )

        # Assertions
        assert result.exit_code == 0, f"Command exited with non-zero code: {result.output}"

        # SettingsManager
        settings_manager_instance.get_all_settings.assert_called_once()

        # Ensure get_section('logger') was called to retrieve logging config
        settings_manager_instance.get_section.assert_called_once_with("logger")

        # TranslationManager: Ensure configure was called
        translation_manager_instance.configure.assert_called_once_with(
            language="en",  # Assuming 'en' is the default from settings or hardcoded
            translation_domain=None,  # Assuming these are None by default
            locale_dir=None,
        )

        # AppContext: Ensure AppContext.create was called with the correct manager instances
        AppContext.create.assert_called_once_with(
            settings_instance=settings_manager_instance,
            translator_instance=translation_manager_instance,
        )

        # Logging Manager: Ensure apply_configuration was called
        # IMPORTANT: The log_config argument here should match what settings_manager_instance.get_section("logger") returns
        expected_log_config = settings_manager_instance.get_section.return_value  # Get the mocked return value
        logging_manager_instance.apply_configuration.assert_called_once_with(
            cli_log_level=logging.INFO,  # As verbose=0 maps to WARNING in your VERBOSITY_LEVELS
            enable_console_logging=True,
            log_config=settings_manager_instance.get_section("logger"),
            translator=translation_manager_instance,
        )

        for log_entry in caplog_structlog:
            print(log_entry)

        assert "Translated: Starting CLI in generate-reports mode" in result.stdout
        assert "Translated: Verbose logging enabled." in result.stdout

        assert "Translated: Error in generate-reports mode" not in result.stdout  # Ensure no error message


def test_reports_command_success_without_existing_results(
    mock_report_manager,
    mock_report_generator,
    mock_check_connect,
    runner,
    tmp_path,
):
    """
    Test successful report generation when no previous results exist,
    triggering new checks.
    """
    # Setup mocks for no existing results scenario
    mock_report_manager.results_exists.return_value = False
    mock_check_connect.ntp_results = ["new_ntp_res"]
    mock_check_connect.url_results = ["new_url_res"]

    # Define paths for options
    reports_dir = tmp_path / "my_reports_new"
    data_dir = tmp_path / "my_data_new"
    config_file = tmp_path / "config.toml"
    config_file.touch()  # Create dummy config file

    # Invoke the command
    result = runner.invoke(
        cli_main.main_app,
        [
            "--reports-dir",
            str(reports_dir),
            "--data-dir",
            str(data_dir),
            "--config-file",
            str(config_file),
            "--language",
            "de",
            "report",
        ],
    )

    # Assertions
    assert result.exit_code == 0
    assert "Translated: Starting CLI in generate-reports mode" in result.stdout

    # Verify CheckConnect was initialized and run
    mock_check_connect.assert_called_once_with(context=mock_app_context.return_value)
    mock_check_connect.run_all_checks.assert_called_once()

    # Verify ReportManager.from_params was called (even if no existing results)
    mock_report_manager.from_params.assert_called_once_with(context=mock_app_context.return_value, data_dir=data_dir)
    mock_report_manager.results_exists.assert_called_once()
    mock_report_manager.load_previous_results.assert_not_called()  # Should not be called

    # Verify ReportGenerator.from_params and generate_reports were called with new results
    mock_report_generator.from_params.assert_called_once_with(
        context=mock_app_context.return_value, output_dir=reports_dir
    )
    mock_report_generator.generate_reports.assert_called_once_with(
        ntp_results=["new_ntp_res"], url_results=["new_url_res"]
    )
    assert "Translated: Error in generate-reports mode" not in result.stdout


def test_reports_command_exit_exception_error(
    mock_report_manager,
    runner,
    tmp_path,
):
    """
    Test error handling when an ExitExceptionError occurs.
    """
    from checkconnect.exceptions import ExitExceptionError

    # Setup mocks to raise ExitExceptionError
    mock_report_manager.from_params.side_effect = ExitExceptionError("Test error")

    config_file = tmp_path / "config.toml"
    config_file.touch()

    # Invoke the command
    result = runner.invoke(
        cli_main.main_app,
        ["--config-file", str(config_file), "report"],
    )

    # Assertions
    assert result.exit_code == 1
    assert "Translated: Error in generate-reports mode" in result.stderr  # Use stderr for exceptions

    # Ensure initialize_app_context was called
    mock_initialize_app_context.assert_called_once()
    # Ensure ReportManager.from_params was called (as it raised the error)
    mock_report_manager.from_params.assert_called_once()
    # Ensure generate_reports was not called as an error occurred early
    mock_report_generator.generate_reports.assert_not_called()


def test_reports_command_default_paths(
    mock_report_manager,
    mock_report_generator,
    runner,
    tmp_path,
):
    """
    Test that the command works correctly without explicitly providing
    reports_dir and data_dir, relying on default option definitions.
    """
    mock_report_manager.results_exists.return_value = True
    mock_report_manager.load_previous_results.return_value = ([], [])

    config_file = tmp_path / "config.toml"
    config_file.touch()

    # Invoke the command without --reports-dir or --data-dir
    result = runner.invoke(
        cli_main.main_app,
        ["--config-file", str(config_file), "report"],
    )

    assert result.exit_code == 0

    # Verify ReportManager.from_params and ReportGenerator.from_params
    # were called. The actual default paths would depend on get_data_dir_option_definition
    # and get_report_dir_option_definition, which are usually dynamic (e.g., based on XDG).
    # For this test, we just check they were called. The specific path values
    # would need more complex mocking if we want to assert the *exact* default paths.
    # However, since they are 'None' in the function signature, we'd expect them
    # to be resolved by the respective `get_..._option_definition()` functions
    # before being passed to `from_params`. This test asserts the flow.
    mock_report_manager.from_params.assert_called_once_with(
        context=mock_app_context.return_value,
        data_dir=None,  # or whatever the default from the option definition would be
    )
    mock_report_generator.from_params.assert_called_once_with(
        context=mock_app_context.return_value,
        output_dir=None,  # or whatever the default from the option definition would be
    )


def test_report_command_with_help_option(
    mocker: Any,
    runner: CliRunner,
):
    """
    Test that 'run summary --help' displays the help message specific to the 'run' command.
    """
    result = runner.invoke(cli_main.main_app, ["report", "--help"])
    print(result.stdout)

    assert result.exit_code == 0
    # Headers
    assert "Usage: cli report [OPTIONS]" in result.output
    assert " Generate HTML and PDF reports from the most recent connectivity test results." in result.output
    # Args
    assert "reports_dir (str): Path to store to the last check results." in result.output
    assert "summary_format (str): Output format for the summary ('text', 'markdown', 'html')." in result.output
    # Options
    assert "--help          Show this message and exit." in result.output
    # Configuration
    assert (
        "--reports_dir  -r      DIRECTORY             Directory where reports will be saved (overrides config)"
        in result.output
    )
    # ---
    # You might still see some initialization logs due to the setup,
    # but the important part is that the help message is correct.
    captured = capsys.readouterr()
    assert "[INFO] checkconnect.config.logging_manager: Full logging configuration applied." in captured.out
