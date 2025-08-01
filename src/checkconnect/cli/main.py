# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Main entry point for the CheckConnect application.

This script dispatches between the command-line interface (CLI) and
the graphical user interface (GUI), based on the selected mode. It handles
global application initialization, including settings, translation, and logging,
before handing control to specific subcommands or the GUI.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path  # noqa: TC003
from typing import Annotated, Any

import structlog
import typer
from rich.console import Console

from checkconnect import __about__
from checkconnect.cli.gui_app import gui_app

# from checkconnect.cli.summary_app import summary_app
from checkconnect.cli.options import (
    get_config_option_definition,
    get_language_option_definition,
    get_verbose_option_definition,
)
from checkconnect.cli.report_app import report_app

# Import sub-commands
from checkconnect.cli.run_app import run_app
from checkconnect.cli.summary_app import summary_app
from checkconnect.config.appcontext import AppContext

# Import your bootstrap logging function (ensure this file exists)
from checkconnect.config.logging_bootstrap import bootstrap_logging

# Import your singleton managers
from checkconnect.config.logging_manager import VERBOSITY_LEVELS, LoggingManager, LoggingManagerSingleton
from checkconnect.config.settings_manager import SettingsManager, SettingsManagerSingleton
from checkconnect.config.translation_manager import TranslationManager, TranslationManagerSingleton
from checkconnect.exceptions import ExitExceptionError, LogHandlerError  # Import for specific error handling

# Initialize Typer CLI app and Rich console
main_app = typer.Typer(
    name="cli",
    help="Check network connectivity and generate reports - CLI or GUI",
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)
"""
The main Typer application instance for CheckConnect.

This instance serves as the root command for the CLI, providing global options
and dispatching to various subcommands (run, report, summary) or the GUI.
It is configured to use rich markup for enhanced terminal output.
"""

main_app.add_typer(
    run_app,
    help=f"Run {__about__.__app_name__} in CLI mode (run tests).",
)

main_app.add_typer(
    report_app,
    help=f"Run {__about__.__app_name__} in CLI mode (generate reports).",
)

main_app.add_typer(
    summary_app,
    help=f"Run {__about__.__app_name__} in CLI mode (show summary).",
)

main_app.add_typer(
    gui_app,
    help=f"Run {__about__.__app_name__} in GUI mode.",
)

console = Console()
"""A Rich Console instance for direct terminal output."""

# --- Phase 1: Bootstrap Logging (GLOBAL, runs immediately on import) ---
# This is crucial. It ensures structlog is minimally configured BEFORE
# any other application code or Typer callbacks try to get a logger.
bootstrap_logging()


# --- Global Logger for main.py ---
# This logger will initially use the bootstrap configuration, and then
# be effectively re-configured by LoggingManagerSingleton after settings load.
# 🆕 Dynamic logger instead of static `main_logger()`
def main_logger() -> structlog.BoundLogger:
    """
    Return a structlog BoundLogger instance specifically for the main application module.

    This logger is used for critical initialization messages before the full
    logging configuration is applied.
    """
    return structlog.get_logger("main")


def _version_callback(*, value: bool = False) -> None:
    """
    Display the application version and exit.

    Args:
    ----
        value (bool): Whether to display the version. This option is eagerly
                      evaluated by Typer.
    """
    if value:
        console.print(
            f"[bold blue]{__about__.__app_name__}[/] version: [bold green]{__about__.__version__}[/]",
        )
        sys.exit()


# --- Helper Functions for Initialization ---


def _initialize_settings_manager(config_file: Path | None) -> SettingsManager:
    """
    Initialize the SettingsManager Singleton and returns its instance.

    Attempts to load application settings from the specified configuration file
    or default locations. Logs any initialization errors and exits on critical failure.

    Args:
    ----
        config_file (Path | None): Optional path to a custom configuration file.

    Returns:
    -------
        SettingsManager: The initialized SettingsManager instance.

    Raises:
    ------
        typer.Exit: If a critical error occurs during settings initialization,
                    the application exits with status code 1.
    """
    main_logger().debug("Main callback: Initializing SettingsManager...")
    try:
        settings_manager = SettingsManagerSingleton.get_instance()
        SettingsManagerSingleton.initialize_from_context(config_path=config_file)

    except Exception as e:
        main_logger().exception(
            "Main callback: Failed to initialize SettingsManager or load configuration!", exc_info=e
        )
        console.print(f"[bold red]Critical Error:[/bold red] Failed to load application configuration: {e}")
        raise typer.Exit(1) from e
    else:
        main_logger().info("Main callback: SettingsManager initialized and configuration loaded.")
        for err in SettingsManagerSingleton.get_initialization_errors():
            main_logger().warning("Main callback: SettingsManager setup warning:", error_details=str(err))
        return settings_manager

def _initialize_translation_manager(language: str | None, app_config: dict[str, Any]) -> TranslationManager:
    """
    Initialize the TranslationManager Singleton and returns its instance.

    Configures the translation services based on the provided language or
    the default language from application settings. Logs any initialization
    errors and exits on critical failure.

    Args:
    ----
        language (str | None): Optional language code (e.g., "en", "de") to override
                               the default from settings.
        app_config (dict[str, Any]): The full application configuration dictionary,
                                     used to retrieve the default language if not specified.

    Returns:
    -------
        TranslationManager: The initialized TranslationManager instance.

    Raises:
    ------
        typer.Exit: If a critical error occurs during translation initialization,
                    the application exits with status code 1.
    """
    main_logger().debug("Main callback: Initializing TranslationManager...")
    try:
        translation_manager = TranslationManagerSingleton.get_instance()
        TranslationManagerSingleton.configure_instance(
            language=language or app_config.get("general", {}).get("default_language", "en")
        )

    except Exception as e:
        main_logger().exception("Main callback: Failed to initialize TranslationManager: ", exc_info=e)
        console.print(f"[bold red]Critical Error:[/bold red] Failed to initialize translation services: {e}")
        raise typer.Exit(1) from e
    else:
        main_logger().info("Main callback: TranslationManager initialized.")
        for err in TranslationManagerSingleton.get_initialization_errors():
            main_logger().warning("Main callback: TranslationManager setup warning:", error_details=str(err))
        return translation_manager

def _configure_logging_manager(*, app_context: AppContext, verbose: int, is_cli_mode: bool) -> LoggingManager:
    """
    Configure the LoggingManager Singleton and returns its instance.

    Applies the full logging configuration based on application settings,
    CLI verbosity level, and whether the application is running in CLI mode
    (which affects console logging). Logs critical errors and exits on failure.

    Args:
    ----
        app_context (AppContext): The application context containing settings and translator.
        verbose (int): The verbosity level provided via CLI (e.g., 0, 1, 2).
        is_cli_mode (bool): True if the application is running in CLI mode, False otherwise.

    Returns:
    -------
        LoggingManager: The initialized and configured LoggingManager instance.

    Raises:
    ------
        typer.Exit: If a critical error occurs during logging configuration,
                    the application exits with status code 1.
    """
    main_logger().debug("Main callback: Configuring full LoggingManager via AppContext...")

    try:
        # Determine cli_log_level from the verbose integer using your VERBOSITY_LEVELS
        # The .get() with a default is good practice in case 'verbose' is out of range.
        # If verbose=0 maps to WARNING and you want to show 'almost nothing',
        # that's consistent with typical logging verbosity (WARNING is less verbose than INFO/DEBUG).
        cli_log_level = VERBOSITY_LEVELS.get(verbose, logging.WARNING)  # Fallback if verbose is out of bounds
        if cli_log_level == logging.WARNING and verbose not in VERBOSITY_LEVELS:
            main_logger().warning(
                "Main callback: Verbose level provided by CLI is out of defined range. Defaulting CLI log level to WARNING.",
                verbose_input=verbose,
            )

        main_logger().debug(
            "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager.",
            verbose_input=verbose,
            derived_cli_log_level=logging.getLevelName(cli_log_level),
        )

        LoggingManagerSingleton.initialize_from_context(
            app_context=app_context,
            cli_log_level=cli_log_level,  # Pass the derived CLI level
            enable_console_logging=is_cli_mode,
        )

        logging_manager = LoggingManagerSingleton.get_instance()


    except LogHandlerError as e:
        main_logger().exception("Main callback: Critical logging setup error:", exc_info=e)
        console.print(f"[bold red]Critical Error:[/bold red] Failed to set up core logging handlers: {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        main_logger().exception(
            "Main callback: Unexpected error during full logging configuration:", exc_info=e
        )
        console.print(f"[bold red]Critical Error:[/bold red] Unexpected error during logging setup: {e}")
        raise typer.Exit(1) from e
    else:
        main_logger().info("Main callback: Full logging configured based on application settings and CLI options.")
        for err in LoggingManagerSingleton.get_initialization_errors():
            main_logger().warning("Main callback: LoggingManager setup warning:", error_details=str(err))
        return logging_manager

@main_app.callback()
def main_callback(
    ctx: typer.Context,
    language: Annotated[str | None, get_language_option_definition()] = None,
    verbose: Annotated[int, get_verbose_option_definition()] = 0,
    config_file: Annotated[Path | None, get_config_option_definition()] = None,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
) -> None:
    """
    CheckConnect is a CLI tool for network connectivity checks.

    This is the main callback function for the Typer CLI application. It handles
    global options such as language, verbosity, and configuration file path.
    It orchestrates the initialization of core application services (Settings,
    Translation, and Logging Managers) and prepares the Typer context for
    subcommands.

    Args:
    ----
        ctx (typer.Context): The Typer context object, used to pass data
                              between the main callback and subcommands.
        language (str | None): Optional language code to use for translations.
                               Defaults to the system's default or configuration.
        verbose (int): Verbosity level (0=warning, 1=info, 2=debug).
        config_file (Path | None): Optional path to a custom configuration file.
        _version (bool | None): Internal option to trigger version display.
                                Handled by `_version_callback`.

    Raises:
    ------
        typer.Exit: If any critical initialization step fails, the application
                    will exit with a non-zero status code.
    """
    main_logger().debug("Main callback: is starting!")

    main_logger().debug(
        "CLI Args",
        language=language,
        verbose=verbose,
        config_file=str(config_file) if config_file else None,
    )

    # Determine execution mode (CLI vs. GUI) based on the invoked subcommand
    is_cli_mode = ctx.invoked_subcommand in ["run", "report", "summary"]
    is_gui_mode = ctx.invoked_subcommand == "gui"

    try:
        # --- Phase 2: Initialize SettingsManager Singleton ---
        settings_manager = _initialize_settings_manager(config_file)
        app_config = settings_manager.get_all_settings()

        # --- Phase 3: Initialize TranslationManager Singleton ---
        translation_manager = _initialize_translation_manager(language, app_config)

        # --- Phase 4: Create AppContext Instance ---
        app_context = AppContext.create(settings_instance=settings_manager, translator_instance=translation_manager)
        main_logger().debug("Main callback: AppContext created with initialized managers.")

        # --- Phase 5: Configure Full Logging via LoggingManager Singleton ---
        logging_manager = _configure_logging_manager(app_context=app_context, verbose=verbose, is_cli_mode=is_cli_mode)

        # --- Phase 6: Store parsed option values and managers in the context object for subcommands ---
        ctx.ensure_object(dict)
        if ctx.obj is None:
            ctx.obj = {}  # CRITICAL: Initialize ctx.obj as a dictionary if it's None

        ctx.obj.update(
            language=language,
            verbose_mode=verbose,
            config_file=config_file,
            is_cli_mode=is_cli_mode,
            is_gui_mode=is_gui_mode,
            settings_manager=SettingsManagerSingleton.get_instance(),
            translation_manager=TranslationManagerSingleton.get_instance(),
            logging_manager=logging_manager,
            app_context=app_context,
        )

        main_logger().debug("Main callback: All core services initialized and context prepared for subcommands.")

    except typer.Exit:
        # If an internal component or Typer itself raises typer.Exit,
        # allow it to propagate without further custom printing,
        # as it's typically already handled by Typer.
        # This is important if e.g. _version_callback raises typer.Exit
        # but your generic Exception handler above would catch it.
        raise  # Re-raise the typer.Exit exception to be handled by the runner.
    except ExitExceptionError as e:
        # Catch specific application-level GUI errors that should lead to an explicit exit
        console.print(f"[bold red]Critical Error:[/bold red] Cannot start GUI due to application error:{e}")
        main_logger().exception(app_context.gettext("Cannot start GUI due to application error."), exc_info=e)
        raise typer.Exit(1) from e
    except Exception as e:
        # This is your custom error handling path for unexpected errors
        critical_message = "Critical Error: An unexpected error occurred during application startup: {e}"
        main_logger().critical(critical_message, exc_info=e)
        console.print(f"[bold red]{critical_message} {e}[/bold red]")  # This is your custom output
        raise typer.Exit(code=1) from e


def main() -> None:
    """Invoke the Typer application to dispatch to the appropriate subcommand or the GUI."""
    main_app()


if __name__ == "__main__":
    main()
