# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Tests for the GUI subcommand in Typer main_app (as a submodule).

This ensures the main_app correctly routes to the GUI command, initializes
AppContext, and calls startup.run with the right context.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from pydantic_core.core_schema import ExpectedSerializationTypes
from structlog.typing import EventDict
import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock

from checkconnect.config.settings_manager import SettingsManager
from checkconnect.cli import main as cli_main
from checkconnect.cli.run_app import run_app
from checkconnect.exceptions import ExitExceptionError


def test_run_command_success(
    mocker,
    mock_app_context,
    patch_checkconnect,
    runner: CliRunner,
    caplog_structlog: list[EventDict],
):
    """
    Ensure run_command completes successfully when CheckConnect runs without error.
    """
    mock_check = patch_checkconnect.return_value
    mock_check.run_all_checks.return_value = None

    result = runner.invoke(cli_main.main_app, ["run"])

    assert result.exit_code == 0
    mock_check.run_all_checks.assert_called_once()

    assert any(
        "Full logging configuration applied." in log_entry["event"] and log_entry["log_level"] == "info"
        for log_entry in caplog_structlog
    ), "Full logging configuration not applied"

    assert any(
        "Starting CLI in tests mode" in log_entry["event"] and log_entry["log_level"] == "info"
        for log_entry in caplog_structlog
    ), "CLI not started in tests mode"


def test_run_command_creates_default_config(
    mocker,
    isolated_test_env: dict[str, Path],
    patch_checkconnect,
    runner: CliRunner,
    caplog_structlog: list[EventDict],
):
    """
    Ensure the run command creates a default config.toml if none is specified.
    """

    mock_check = patch_checkconnect.return_value
    mock_check.run_all_checks.return_value = None

    # Get the mocked settings manager from the fixture
    # The actual config.toml file path expected
    expected_config_str = SettingsManager.DEFAULT_SETTINGS_LOCATIONS[0]
    expected_config_path = Path(expected_config_str)

    assert not expected_config_path.exists()  # Pre-condition: file should not exist yet

    result = runner.invoke(cli_main.main_app, ["run"])

    assert result.exit_code == 0

    mock_check.run_all_checks.assert_called_once()

    assert expected_config_path.is_file()  # Post-condition: file should now exist

    assert any(
        "Default configuration written successfully." in log_entry["event"] and log_entry["log_level"] == "info"
        for log_entry in caplog_structlog
    )


def test_run_command_handles_exit_exception(
    mocker,
    patch_checkconnect,
    runner: CliRunner,
    caplog_structlog: list[EventDict],
):
    """
    Ensure ExitExceptionError is handled with logging and clean exit.
    """

    patch_checkconnect.return_value.run_all_checks.side_effect = ExitExceptionError("Controlled failure")

    result = runner.invoke(cli_main.main_app, ["run"])
    print(result.output)

    assert result.exit_code == 1

    for log_entry in caplog_structlog:
        print(log_entry)

    assert any(
        "Error in run_command." in log_entry["event"] and log_entry["log_level"] == "error"
        for log_entry in caplog_structlog
    )


def test_run_command_handles_unexpected_exception(
    mocker,
    patch_checkconnect,
    runner: CliRunner,
    caplog_structlog: list[EventDict],
):
    """
    Ensure unexpected exceptions are logged and cause exit with code 1.
    """

    patch_checkconnect.return_value.run_all_checks.side_effect = RuntimeError("Something went wrong")

    result = runner.invoke(cli_main.main_app, ["run"])

    assert result.exit_code == 1

    assert any(
        "An unexpected error occurred during tests." in log_entry["event"] and log_entry["log_level"] == "error"
        for log_entry in caplog_structlog
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("cli_args", "expected_log_level"),
    [
        ("--verbose", logging.DEBUG),
    ],
)
def test_run_command_with_cli_options(
    mocker,
    patch_checkconnect,
    cli_args,
    expected_log_level,
    tmp_path: Path,
    config_file: Path,
    runner: CliRunner,
    caplog_structlog: list[EventDict],
):
    """
    Test the run command handles verbosity options and passes config to AppContext.
    """
    # Patch the logging manager to inspect cli_log_level
    # mock_logging_manager = mocker.Mock()
    # mock_logging_get = mocker.patch(
    #     "checkconnect.cli.main.LoggingManagerSingleton.initialize_from_context",
    #     return_value=mock_logging_manager,
    # )

    print("CLI-Args: ", cli_args)

    # if cli_args is None:
    #     cli_args = ""

    result = runner.invoke(cli_main.main_app, ["--language", "en", f"--config={config_file}", f"{cli_args}", "run"])

    print(result.output)

    for log_entry in caplog_structlog:
        print(log_entry)

    assert result.exit_code == 0
    patch_checkconnect.assert_called_once()

    # LoggingManager should receive correct verbosity
    # called_args = mock_logging_get.call_args.kwargs
    # print(called_args)
    # assert called_args["cli_log_level"] == expected_log_level


@pytest.mark.unit
def test_run_command_verbose_flag_levels(tmp_path: Path, mocker: Any, mock_dependencies, runner: CliRunner):
    """
    Test that verbosity level maps correctly to log level.
    """
    mock_log_init = mocker.patch("checkconnect.config.logging_manager.LoggingManagerSingleton.initialize_from_context")

    result = runner.invoke(cli_main.main_app, ["run", "-vv"])

    assert result.exit_code == 0
    mock_log_init.assert_called_once()
    args, kwargs = mock_log_init.call_args
    assert kwargs["cli_log_level"] == 0  # logging.NOTSET


def test_run_command_with_help_option(
    mocker: Any,
    runner: CliRunner,
):
    """
    Test that 'run --help' displays the help message specific to the 'run' command.
    """
    result = runner.invoke(cli_main.main_app, ["run", "--help"])
    print(result.stdout)

    assert result.exit_code == 0

    # Headers
    assert "Usage: cli run [OPTIONS]" in result.output
    assert "Run network tests for NTP and HTTPS servers." in result.output

    # Options
    assert "--help          Show this message and exit." in result.output

    # You might still see some initialization logs due to the setup,
    # but the important part is that the help message is correct.
    captured = capsys.readouterr()
    assert "[INFO] checkconnect.config.logging_manager: Full logging configuration applied." in captured.out
