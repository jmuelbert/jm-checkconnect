# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Integration tests for the main CLI application.

These tests verify the behavior of the `main_app` Typer application,
including global option parsing, initialization of core singleton managers,
and proper command dispatch.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from checkconnect.cli.main import main_app
from checkconnect.config.appcontext import AppContext
from tests.utils.common import assert_common_cli_logs, clean_cli_output

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from structlog.typing import EventDict
    from typer.testing import CliRunner


@pytest.fixture
def mock_checkconnect_class(mocker: MockerFixture):
    """
    Mocks the CheckConnect class and its instance methods, including getters.

    This version correctly mocks properties using PropertyMock.
    """
    with patch("checkconnect.cli.run_app.CheckConnect") as mock_cc_class:
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


class TestCliMain:
    """
    Integration test suite for the main CheckConnect CLI application.

    These tests focus on the end-to-end behavior of the CLI's global options
    and the initialization flow of key application components (settings,
    translation, logging) when different CLI arguments are provided.
    """

    @pytest.mark.integration
    def test_main_callback_with_all_options(
        self,
        mock_dependencies: dict[str, Any],
        mock_checkconnect_class: MagicMock,
        config_file: Path,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test the main_callback with all defined CLI options: --language, -v, --config.

        Verifies that the application initializes correctly, passes the CLI
        arguments to the respective managers, and executes the 'run' subcommand.

        Args:
        ----
            mock_dependencies (dict[str, Any]): A fixture providing mocked instances
                                                 of core application managers.
            config_file (Path): A fixture providing a path to a temporary config file.
            runner (CliRunner): Typer's CLI test runner fixture.
            caplog_structlog (list[EventDict]): Pytest fixture to capture structlog events.
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        result = runner.invoke(
            main_app,
            ["--language", "en", "--verbose", "--config", str(config_file), "run"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # --- Assertions ---

        # SettingsManager
        settings_manager_instance.get_all_settings.assert_called_once()

        # TranslationManager
        # If `translation_manager_instance.configure` is called:
        translation_manager_instance.configure.assert_called_once_with(
            language="en", translation_domain=None, locale_dir=None
        )

        # AppContext
        AppContext.create.assert_called_once_with(
            settings_instance=settings_manager_instance,
            translator_instance=translation_manager_instance,
        )

        # Logging Manager
        # Note: The cli_log_level will be logging.INFO because --verbose maps to 1,
        # and 1 maps to INFO in VERBOSITY_LEVELS.
        logging_manager_instance.apply_configuration.assert_called_once_with(
            cli_log_level=logging.INFO,
            enable_console_logging=True,
            log_config=settings_manager_instance.get_section("logger"),
            translator=translation_manager_instance,
        )

        # Checkconnect called?
        # If result doesn't exists generate new results
        mock_checkconnect_class.assert_called_once_with(context=AppContext.create.return_value)
        checkconnect_instance = mock_checkconnect_class.return_value
        checkconnect_instance.run_all_checks.assert_called_once()

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 1
            and e.get("language") == "en"
            and e.get("config_file") == str(config_file)
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

        # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == 1
            and e.get("derived_cli_log_level") == "INFO"
            for e in caplog_structlog
        )

        # 5. Assert "Debug logging is active" (DEBUG)
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

        # Check config file was passed and assigned
        loaded_config_file = settings_manager_instance.loaded_config_file
        assert loaded_config_file == config_file

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("cli_arg", "expected_log_level", "expected_level", "expected_verbose"),
        [
            ("--verbose", logging.INFO, "INFO", 1),
            ("-vv", logging.DEBUG, "DEBUG", 2),
        ],
    )
    def test_verbose_flag_levels(
        self,
        cli_arg: str,
        expected_log_level: int,
        expected_level: str,
        expected_verbose: int,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that verbosity level maps correctly to log level.

        Verifies that the `--verbose` and `-vv` CLI flags correctly set the
        corresponding log levels (INFO and DEBUG respectively) within the
        LoggingManager.

        Args:
        ----
            cli_arg (str): The CLI argument for verbosity (e.g., "--verbose", "-vv").
            expected_log_level (int): The expected numerical logging level (e.g., logging.INFO).
            expected_level (str): The expected string representation of the logging level (e.g., "INFO").
            expected_verbose (int): The integer value passed for the verbose option (e.g., 1, 2).
            mock_dependencies (dict[str, Any]): A fixture providing mocked instances
                                                 of core application managers.
            runner (CliRunner): Typer's CLI test runner fixture.
            caplog_structlog (list[EventDict]): Pytest fixture to capture structlog events.
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        result = runner.invoke(
            main_app,
            [cli_arg, "run"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # Logging Manager
        logging_manager_instance.apply_configuration.assert_called_once_with(
            cli_log_level=expected_log_level,
            enable_console_logging=True,
            log_config=settings_manager_instance.get_section("logger"),
            translator=translation_manager_instance,
        )

        # --- Asserting on Specific Log Entries from Your Output ---

        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == expected_verbose
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

        # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
        assert any(
            e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
            and e.get("log_level") == "debug"
            and e.get("verbose_input") == expected_verbose
            and e.get("derived_cli_log_level") == expected_level
            for e in caplog_structlog
        )

        # 5. Assert "Debug logging is active" (DEBUG)
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
        assert not any(e.get("log_level") in ["error", "critical"] for e in caplog_structlog)

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("cli_arg", "language"),
        [("--language", "en"), ("-l", "de"), ("--language", "xx")],
    )
    def test_several_languages(
        self,
        cli_arg: str,
        language: str,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that different language options are correctly handled by the TranslationManager.

        Verifies that the `--language` and `-l` CLI flags correctly configure the
        TranslationManager with the specified language.

        Args:
        ----
            cli_arg (str): The CLI argument for language (e.g., "--language", "-l").
            language (str): The language code to test (e.g., "en", "de", "xx").
            mock_dependencies (dict[str, Any]): A fixture providing mocked instances
                                                 of core application managers.
            runner (CliRunner): Typer's CLI test runner fixture.
            caplog_structlog (list[EventDict]): Pytest fixture to capture structlog events.
        """
        # Extract mocks
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        # Runner
        result = runner.invoke(
            main_app,
            [cli_arg, language, "run"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # Translation Manager
        translation_manager_instance.configure.assert_called_once_with(
            language=language,
            translation_domain=None,
            locale_dir=None,
        )

        # --- Asserting on Specific Log Entries from Your Output ---
        assert_common_cli_logs(caplog_structlog)

        # Assert CLI Args
        assert any(
            e.get("event") == "CLI Args"
            and e.get("log_level") == "debug"
            and e.get("verbose") == 0
            and e.get("language") == language
            and e.get("config_file") is None
            for e in caplog_structlog
        )

        # At the end of the assert block for successful tests:
        assert not any(e.get("log_level") == "error" or e.get("log_level") == "critical" for e in caplog_structlog), (
            "Unexpected ERROR or CRITICAL logs found in a successful test run."
        )

    @pytest.mark.integration
    def test_main_callback_raises_on_config_load_failure(
        self,
        mocker: MockerFixture,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Simulate a config load failure and assert graceful typer.Exit(1).

        Verifies that if `SettingsManagerSingleton.initialize_from_context`
        raises an exception, the application logs a critical error, prints
        a user-friendly message to the console, and exits with status code 1.

        Args:
        ----
            mocker (MockerFixture): Pytest-mock fixture for patching.
            mock_dependencies (dict[str, Any]): A fixture providing mocked instances
                                                 of core application managers.
            runner (CliRunner): Typer's CLI test runner fixture.
            caplog_structlog (list[EventDict]): Pytest fixture to capture structlog events.
        """
        mocker.patch(
            "checkconnect.config.settings_manager.SettingsManagerSingleton.initialize_from_context",
            side_effect=RuntimeError("Boom"),
        )

        result = runner.invoke(
            main_app, ["run"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        assert result.exit_code == 1, f"Unexpected success or wrong exit code: {result.output}"

        assert "Critical Error" in cleaned
        assert "Failed to load application configuration" in cleaned

        # --- Asserting on Specific Log Entries from Your Output ---
        # 1. Assert initial CLI startup (DEBUG)
        assert any(
            e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in caplog_structlog
        )

        # Assert CLI Args
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
            e.get("event") == "Main callback: Initializing SettingsManager..." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # At the end of the assert block for successful tests:
        assert any(
            "exc_info" in e
            and e.get("event") == "Main callback: Failed to initialize SettingsManager or load configuration!"
            and isinstance(e.get("exc_info"), RuntimeError)
            and str(e.get("exc_info")) == "Boom"
            and e.get("log_level") == "error"
            for e in caplog_structlog
        ), "Expected critical log for config load failure not found."

    @pytest.mark.integration
    def test_main_callback_with_invalid_config_file(
        self,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
    ) -> None:
        """
        Test CLI behavior when an invalid config path (file doesn't exist) is provided.

        Verifies that Typer's built-in validation catches the non-existent file path
        before the main callback runs, resulting in a non-zero exit code and an
        appropriate error message in the output.

        Args:
        ----
            mock_dependencies (dict[str, Any]): A fixture providing mocked instances
                                                 of core application managers (though
                                                 they might not be fully initialized here).
            runner (CliRunner): Typer's CLI test runner fixture.
        """
        non_existent_path = Path("/does/not/exist.toml")
        result = runner.invoke(
            main_app,
            ["--config", str(non_existent_path), "run"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        # Typer automatically handles "file must exist" for Path types
        assert result.exit_code != 0, f"Expected non-zero exit code for invalid config file, got 0: {result.output}"
        assert "Invalid value for '--config'" in cleaned
        assert str(non_existent_path) in cleaned # Ensure the path is mentioned in the error

        # Ensure no managers were initialized if the config file was invalid
        mock_dependencies["settings_manager_instance"].get_all_settings.assert_not_called()
        mock_dependencies["translation_manager_instance"].configure.assert_not_called()
        mock_dependencies["logging_manager_instance"].apply_configuration.assert_not_called()

    @pytest.mark.integration
    def test_main_with_help_option(
        self,
        runner: CliRunner,
    ) -> None:
        """
        Test that the '--help' option displays the main application help message.

        Verifies that the output contains expected sections like Usage, Options,
        and Commands, and that the exit code is 0.

        Args:
        ----
            runner (CliRunner): Typer's CLI test runner fixture.
        """

        result = runner.invoke(
            main_app,
            ["--help"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # Header
        assert "Usage: cli [OPTIONS] COMMAND [ARGS]..." in cleaned
        assert "Check network connectivity and generate reports - CLI or GUI" in cleaned
        # Options
        assert "--version -V Show the application version and exit." in cleaned
        assert "--install-completion Install completion for the current shell." in cleaned
        assert (
            "--show-completion Show completion for the current shell, to copy it or customize the installation."
            in cleaned
        )
        assert "--help Show this message and exit." in cleaned
        # Localization
        assert "Localization" in cleaned
        assert "--language -l TEXT Language (e.g., 'en', 'de'). [default: None]" in cleaned
        # Logging
        assert "Logging" in cleaned
        assert (
            "--verbose -v INTEGER Increase verbosity. Default logging level is WARNING. Use -v to enable INFO messages. -vv to enable DEBUG messages. Additional -v flags have no further effect."
            in cleaned
        )
        # Configuration
        assert "Configuration" in cleaned
        assert (
            "--config -c FILE Path to the config file. A default one is created if missing. [default: None]"
            in cleaned
        )
        # Commands
        assert "Commands" in cleaned
        assert "run Run network tests for NTP and HTTPS servers." in cleaned
        assert (
            "report Generate HTML and PDF reports from the most recent connectivity test results." in cleaned
        )
        assert "summary Generate a summary of the most recent connectivity test results." in cleaned
        assert "gui Run CheckConnect in graphical user interface (GUI) mode." in cleaned

    @pytest.mark.integration
    def test_main_with_version_option(self, runner: CliRunner) -> None:
        """
        Ensure the '--version' flag prints the application version and exits early.

        Verifies that invoking the main app with `--version` results in a 0 exit code
        and the version string in the output, without running the main callback logic.

        Args:
        ----
            runner (CliRunner): Typer's CLI test runner fixture.
        """

        result = runner.invoke(
            main_app,
            ["--version"],
            env={
                "NO_COLOR": "1",   # Rich disables colors
                "TERM": "dumb",    # disables most TTY formatting
                "CLICOLOR_FORCE": "0",  # if using rich-click, force no color
            },
            catch_exceptions=False,  # no swallowing, pytest will see the error
        )
        # Remove all whitespace differences (spaces, newlines, carriage returns)
        cleaned = clean_cli_output(result.stdout)

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"
        assert "CheckConnect" in cleaned
        assert "version" in cleaned.lower()


if __name__ == "__main__":
    main_app()
