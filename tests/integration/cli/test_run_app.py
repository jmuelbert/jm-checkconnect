# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Tests for the GUI subcommand in Typer main_app (as a submodule).

This ensures the main_app correctly routes to the GUI command, initializes
AppContext, and calls startup.run with the right context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import logging
import tempfile
from pathlib import Path

from pydantic_core.core_schema import ExpectedSerializationTypes

import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from checkconnect.config.appcontext import AppContext
from checkconnect.cli import main as cli_main
from checkconnect.cli.run_app import run_app
from checkconnect.exceptions import ExitExceptionError


from tests.utils.common import assert_common_initialization, assert_common_cli_logs

if TYPE_CHECKING:
    # If EventDict is a specific type alias in structlog
    from structlog.typing import EventDict
else:
    EventDict = dict[str, Any]


@pytest.fixture
def mock_checkconnect_class():
    """Mocks the CheckConnect class and its instance methods, including getters."""
    with patch("checkconnect.cli.run_app.CheckConnect") as mock_cc_class:
        mock_instance = MagicMock(name="CheckConnect_instance")
        mock_instance.run_all_checks.return_value = None

        # NEU: Mock die Getter-Methoden anstatt der direkten Attribute
        mock_instance.get_ntp_results.return_value = ["mocked_ntp_data_from_getter"]
        mock_instance.get_url_results.return_value = ["mocked_url_data_from_getter"]

        mock_cc_class.return_value = mock_instance
        yield mock_cc_class


class TestCliRun:
    @pytest.mark.integration
    def test_run_command_success(
        self,
        mock_dependencies: dict[str, Any],
        mock_checkconnect_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Ensure run_command completes successfully when CheckConnect runs without error.
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

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            cli_main.main_app,
            ["run"],
            env=test_env,
        )

        assert result.exit_code == 0, f"Command exited with non-zero code: {result.exception}"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        mock_checkconnect_class.assert_called_once_with(context=AppContext.create.return_value)
        checkconnect_instance = mock_checkconnect_class.return_value
        checkconnect_instance.run_all_checks.assert_called_once()

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
            e.get("event") == "Starting CLI in tests mode" and e.get("log_level") == "info" for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    def test_run_command_handles_exit_exception(
        self,
        mock_dependencies: dict[str, Any],
        mock_checkconnect_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Ensure ExitExceptionError is handled with logging and clean exit.
        """
        # Arrange
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        app_context_instance = mock_dependencies["app_context_instance"]

        # Ensure AppContext.create.return_value is readily available for later assertions
        assert AppContext.create.return_value == app_context_instance

        checkconnect_instance = mock_checkconnect_class.return_value
        checkconnect_instance.run_all_checks.side_effect = ExitExceptionError("Controlled failure")

        # Invoke the command
        result = runner.invoke(
            cli_main.main_app,
            ["run"],
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "Cannot run checks." in result.stdout, (
            "Expected 'Cannot start generate reports for checkconnect.' in stdout"
        )
        assert "Controlled failure" in result.stdout, "Expected 'Controlled failure' in stdout"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        mock_checkconnect_class.assert_called_once_with(context=AppContext.create.return_value)

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

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert any(
            e.get("log_level") in ["error", "critical"] and e.get("event") == "Error in Checks: Controlled failure"
            for e in caplog_structlog
        )

    @pytest.mark.integration
    def test_run_command_handles_unexpected_exception(
        self,
        mock_dependencies: dict[str, Any],
        mock_checkconnect_class: MagicMock,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Ensure unexpected exceptions are logged and cause exit with code 1.
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
            ["run"],
        )

        # Assert CLI command exits with code 0
        assert result.exit_code == 1, f"Missing exception: {result.output}"
        assert "An unexpected error occurred during checks." in result.stdout, (
            "Expected 'Cannot start generate reports for checkconnect.' in stdout"
        )
        assert "Something went wrong" in result.stdout, "Expected 'Controlled failure' in stdout"

        # Common initialization assertions
        assert_common_initialization(
            settings_manager_instance,
            logging_manager_instance,
            translation_manager_instance,
            expected_cli_log_level=logging.WARNING,  # Default from verbose=0 in cli_main
            expected_language="en",
            expected_console_logging=True,
        )

        mock_checkconnect_class.assert_called_once_with(context=AppContext.create.return_value)

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

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert any(
            e.get("log_level") in ["error", "critical"]
            and e.get("event") == "An unexpected error occurred during checks. (Something went wrong)"
            for e in caplog_structlog
        )

    @pytest.mark.integration
    def test_run_command_with_help_option(
        self,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that 'run --help' displays the help message specific to the 'run' command.
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

        result = runner.invoke(cli_main.main_app, ["run", "--help"], env=test_env)

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
        assert "Usage: cli run [OPTIONS]" in result.output
        assert "Run network tests for NTP and HTTPS servers." in result.output

        # Options
        assert "--help          Show this message and exit." in result.output
