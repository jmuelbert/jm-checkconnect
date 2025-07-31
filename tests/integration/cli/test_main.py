import logging

import sys
from collections.abc import Generator

from typing import TYPE_CHECKING, Any
from pathlib import Path
import structlog
from structlog.typing import EventDict

import pytest
from pytest_mock import MockerFixture

from typer.testing import CliRunner
from checkconnect.cli.main import main_app
from checkconnect.config import logging_manager
from checkconnect.config.logging_manager import LoggingManagerSingleton
from checkconnect.config.appcontext import AppContext

from tests.utils.common import assert_common_cli_logs


class TestCliMain:
    @pytest.mark.integration
    def test_main_callback_with_all_options(
        self,
        mock_dependencies: dict[str, Any],
        config_file: Path,
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test the main_callback with all defined CLI options: --language, -v, --config.
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]
        check_connect_instance = mock_dependencies["check_connect_instance"]

        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            main_app,
            ["--language", "en", "--verbose", "--config", str(config_file), "run"],
            env=test_env,
        )

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # --- Assertions ---

        # SettingsManager
        settings_manager_instance.get_all_settings.assert_called_once()

        # TranslationManager
        # TranslationManagerSingleton.initialize_from_context.assert_called_once_with(language="en")
        # If `translation_manager_instance.configure` is called:
        translation_manager_instance.configure.assert_called_once_with(
            language="en", translation_domain=None, locale_dir=None
        )

        # AppContext
        AppContext.create.assert_called_once_with(
            settings_instance=settings_manager_instance,  # Changed from settings_instance
            translator_instance=translation_manager_instance,  # Changed from translator_instance
        )

        # Logging Manager
        logging_manager_instance.apply_configuration.assert_called_once_with(
            cli_log_level=logging.INFO,  # As `--verbose` in your test typically maps to DEBUG
            enable_console_logging=True,  # Assuming `is_cli_mode` (which is implicit true for runner.invoke) means console logging
            log_config=settings_manager_instance.get_section("logger"),  # Use your mock's return value here
            translator=translation_manager_instance,  # Pass the translation manager mock
        )

        # Checkconnect called?
        check_connect_instance.run_all_checks.assert_called_once()

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
        # This one is tricky if it *always* appears when `caplog_structlog` captures at DEBUG.
        # If it specifically means the *application* is running in debug, then assert.
        # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
        assert any(
            e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
            for e in caplog_structlog
        )

        # Optional: Assert no ERROR/CRITICAL logs in a successful run
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
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        result = runner.invoke(main_app, [cli_arg, "run"])

        print(result.stdout)
        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # Logging Manager
        logging_manager_instance.apply_configuration.assert_called_once_with(
            cli_log_level=expected_log_level,  # As `--verbose` in your test typically maps to DEBUG
            enable_console_logging=True,  # Assuming `is_cli_mode` (which is implicit true for runner.invoke) means console logging
            log_config=settings_manager_instance.get_section("logger"),  # Use your mock's return value here
            translator=translation_manager_instance,  # Pass the translation manager mock
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
        # This one is tricky if it *always* appears when `caplog_structlog` captures at DEBUG.
        # If it specifically means the *application* is running in debug, then assert.
        # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
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
        Test that verbosity level maps correctly to log level.
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        # Runner
        result = runner.invoke(main_app, [cli_arg, language, "run"])

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # Translation Manager
        translation_manager_instance.configure.assert_called_once_with(
            language=language,  # As `--verbose` in your test typically maps to DEBUG
            translation_domain=None,  # Assuming `is_cli_mode` (which is implicit true for runner.invoke) means console logging
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
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Simulate a config load failure and assert graceful typer.Exit(1).
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        mocker.patch(
            "checkconnect.config.settings_manager.SettingsManagerSingleton.initialize_from_context",
            side_effect=RuntimeError("Boom"),
        )

        result = runner.invoke(main_app, ["run"])

        assert result.exit_code == 1, f"Unexpected failure: {result.output}"

        assert "Critical Error" in result.output
        assert "Failed to load application configuration" in result.output

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
            e.get("log_level") == "error"
            or e.get("log_level") == "critical"
            and e.get("event") == "Main callback: Failed to initialize SettingsManager or load configuration!"
            and e.get("error_details") == "Boom"
            for e in caplog_structlog
        )

    @pytest.mark.integration
    def test_main_callback_with_invalid_config_file(
        self,
        mock_dependencies: dict[str, Any],
        runner: CliRunner,
    ):
        """
        Test CLI with invalid config path (file doesn't exist).
        Typer should catch this before callback runs.
        """
        # Extract mocks
        settings_manager_instance = mock_dependencies["settings_manager_instance"]
        logging_manager_instance = mock_dependencies["logging_manager_instance"]
        translation_manager_instance = mock_dependencies["translation_manager_instance"]

        non_existent_path = Path("/does/not/exist.toml")
        result = runner.invoke(main_app, ["--config", str(non_existent_path), "run"])

        # Typer automatically handles "file must exist"
        assert result.exit_code != 0, f"Unexpected failure: {result.output}"
        assert "Invalid value for '--config'" in result.output

    @pytest.mark.integration
    def test_main_with_help_option(
        self,
        runner: CliRunner,
    ) -> None:
        """
        Test that 'run --help' displays the help message specific to the 'run' command.
        """
        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            main_app,
            ["--help"],
            env=test_env,  # Pass the environment variables here
        )

        print(result.stdout)

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"

        # Header
        assert "Usage: cli [OPTIONS] COMMAND [ARGS]..." in result.output
        assert "Check network connectivity and generate reports - CLI or GUI" in result.output
        # Options
        assert "--version             -V        Show the application version and exit." in result.output
        assert "--install-completion            Install completion for the current shell." in result.output
        assert (
            "--show-completion               Show completion for the current shell, to copy it or customize the installation."
            in result.output
        )
        assert "--help                          Show this message and exit. " in result.output
        # Localization
        assert "--language  -l      TEXT  Language (e.g., 'en', 'de'). " in result.output
        # Logging
        assert (
            "--verbose  -v      INTEGER  Increase verbosity. Default logging level is WARNING. Use -v to enable INFO messages. -vv to enable DEBUG messages. Additional -v"
            in result.output
        )  # Corrected from `main_app`
        # Configuration
        assert "--config  -c      FILE  Path to the config file. A default one is created if missing. " in result.output
        # Commands
        assert "run       Run network tests for NTP and HTTPS servers." in result.output
        assert (
            "report    Generate HTML and PDF reports from the most recent connectivity test results." in result.output
        )
        assert "summary   Generate a summary of the most recent connectivity test results." in result.output
        assert "gui       Run CheckConnect in graphical user interface (GUI) mode." in result.output

    @pytest.mark.integration
    def test_main_with_version_option(self, runner: CliRunner) -> None:
        """
        Ensure the --version flag prints version and exits early.
        """
        test_env = {
            "NO_COLOR": "1",  # Disable colors
            "TERM": "dumb",  # Disable advanced terminal features like frames
            "mix_stderr": "False",  # <--- This should be a direct argument to invoke()
            "catch_exceptions": "False",  # <--- And this one too
            # If using rich_click specifically, sometimes CLICOLOR_FORCE=0 helps too
        }

        result = runner.invoke(
            main_app,
            ["--version"],
            env=test_env,  # Pass the environment variables here
        )

        assert result.exit_code == 0, f"Unexpected failure: {result.output}"
        assert "CheckConnect" in result.output
        assert "version" in result.output.lower()


if __name__ == "__main__":
    main_app()
