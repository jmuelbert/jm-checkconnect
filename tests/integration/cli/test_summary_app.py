# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

from pathlib import Path
from rich.console import Console

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from checkconnect.cli import main as cli_main
from checkconnect.config.appcontext import AppContext
from checkconnect.reports.report_manager import OutputFormat, ReportManager

console = Console()


@pytest.fixture
def mock_context(mocker: MagicMock) -> MagicMock:
    logger = mocker.Mock()
    logger.info = mocker.Mock()
    logger.exception = mocker.Mock()

    context = mocker.Mock()
    context.logger = logger
    context.gettext = lambda msg: msg
    return context


@pytest.fixture
def mock_report_manager(mocker: MagicMock) -> ReportManager:
    mock_instance = mocker.Mock()
    mock_instance.load_previous_results.return_value = (["url1"], ["ntp1"])
    mock_instance.get_summary.return_value = "Summary Output"
    mocker.patch(
        "checkconnect.reports.report_manager.ReportManager",
        return_value=mock_instance,
    )
    return mock_instance


class TestCliSummary:
    @pytest.mark.unit
    def test_summary_command_runs_successfully(self, mocker: MockerFixture, runner: CliRunner) -> None:
        """
        Test that the summary subcommand initializes correctly and runs without error.
        Mocks `startup_summary` to prevent actually launching the summary.
        """
        # Mock the startup_summary to prevent actual summary launch
        mocked_summary = mocker.patch("checkconnect.reports.report_manager.ReportManager.get_summary")

        # Run CLI with the 'summary summary' subcommand
        result = runner.invoke(cli_main.main_app, ["run", "--help"])

        console.print(result.output)

        # Assert CLI command exits with code 0
        assert result.exit_code == 0, result.stdout

        # Assert startup_summary was called
        mocked_summary.assert_called_once()

    @pytest.mark.unit
    def test_summary_command_respects_config_and_language(
        self,
        mocker: MockerFixture,
        runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        """Test that the summary command passes config and language correctly."""
        # Patch startup_summary and initialize_app_context to control AppContext
        mock_startup_summary = mocker.patch("checkconnect.summary.startup")

        # Dummy AppContext
        dummy_context = mocker.Mock()
        dummy_context.logger = mocker.Mock()
        dummy_context.gettext = lambda x: x
        mock_initialize.return_value = dummy_context

        config_file = tmp_path / "test_config.toml"
        config_file.write_text("dummy = 'value'")

        result = runner.invoke(
            summary_app,
            ["--config", str(config_file), "--language", "de", "--verbose"],
        )

        print(result.stdout)
        assert result.exit_code == 0
        mock_initialize.assert_called_once()
        mock_startup_summary.assert_called_once_with(context=dummy_context, language="de")
        dummy_context.logger.setLevel.assert_called_once()
        dummy_context.logger.debug.assert_called_once_with("Verbose logging enabled.")
        dummy_context.logger.info.assert_called_once_with(
            "Starting CheckConnect summary...",
        )

    @pytest.mark.unit
    def test_summary_command_logs_exception(
        self,
        mocker: MockerFixture,
    ) -> None:
        """Test that exceptions during summary startup are logged and handled."""
        mock_startup_summary = mocker.patch("checkconnect.summary.startup")
        mock_initialize = mocker.patch(
            "checkconnect.config.appcontext.initialize_app_context",
        )

        dummy_context = mocker.Mock()
        dummy_context.logger = mocker.Mock()
        dummy_context.gettext = lambda x: x
        mock_initialize.return_value = dummy_context

        mock_startup_summary.side_effect = ExitExceptionError("summary init failed")

        result = runner.invoke(summary_app)

        print(result.stdout)
        assert result.exit_code == 1
        dummy_context.logger.exception.assert_called_once_with("Can't startup summary!")

    def test_cli_summary_text_format(
        self,
        tmp_path: Path,
        mock_report_manager: MagicMock,
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("[dummy]")

        result = runner.invoke(
            summary_app,
            [
                "--config",
                str(config_file),
                "--language",
                "en",
                "--format",
                "text",
            ],
        )

        print(result.stdout)

        assert result.exit_code == 0
        assert "Summary Output" in result.stdout
        mock_report_manager.get_summary.assert_called_once_with(
            ntp_results=["ntp1"],
            url_results=["url1"],
            format=OutputFormat.text,
        )

    def test_cli_summary_html_format(
        self,
        tmp_path: Path,
        mock_report_manager: MagicMock,
    ) -> None:
        config_file = tmp_path / "config.toml"
        config_file.write_text("[dummy]")

        result = runner.invoke(
            summary_app,
            [
                "--config",
                str(config_file),
                "--language",
                "en",
                "--format",
                "html",
            ],
        )

        print(result.stdout)

        assert result.exit_code == 0
        assert "Summary Output" in result.stdout
        mock_report_manager.get_summary.assert_called_once_with(
            ntp_results=["ntp1"],
            url_results=["url1"],
            format=OutputFormat.html,
        )


def test_report_command_with_help_option(
    mocker: Any,
    runner: CliRunner,
):
    """
    Test that 'run summary --help' displays the help message specific to the 'run' command.
    """
    result = runner.invoke(cli_main.main_app, ["summary", "--help"])
    print(result.stdout)

    assert result.exit_code == 0
    # Headers
    assert "Usage: cli summary [OPTIONS]" in result.output
    assert "Generate a summary of the most recent connectivity test results." in result.output
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
    assert (
        "--data_dir     -d      DIRECTORY             Directory where data will be saved. Default used the system defined user data dir. "
        in result.output
    )
    assert "--format       -f        Output format: text, markdown, html." in result.output
    # You might still see some initialization logs due to the setup,
    # but the important part is that the help message is correct.
    captured = capsys.readouterr()
    assert "[INFO] checkconnect.config.logging_manager: Full logging configuration applied." in captured.out
