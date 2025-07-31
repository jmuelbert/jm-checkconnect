# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Main entry point for the CheckConnect application.

This script dispatches between the command-line interface (CLI) and
the graphical user interface (GUI), based on the selected mode.
"""

from __future__ import annotations

from pathlib import Path

import logging
import sys
from typing import Annotated

import structlog
import typer
from rich.console import Console

from checkconnect import __about__

# from checkconnect.cli.summary_app import summary_app
from checkconnect.cli.options import (
    get_config_option_definition,
    get_language_option_definition,
    get_verbose_option_definition,
)

# Import your singleton managers
from checkconnect.config.logging_manager import LoggingManagerSingleton, LoggingManager, VERBOSITY_LEVELS
from checkconnect.config.settings_manager import SettingsManagerSingleton, SettingsManager
from checkconnect.config.translation_manager import TranslationManagerSingleton, TranslationManager
from checkconnect.config.appcontext import AppContext

# Import your bootstrap logging function (ensure this file exists)
from checkconnect.config.logging_bootstrap import bootstrap_logging
from checkconnect.exceptions import LogHandlerError  # Import for specific error handling

# Import sub-commands
from checkconnect.cli.run_app import run_app
from checkconnect.cli.summary_app import summary_app
from checkconnect.cli.gui_app import gui_app
from checkconnect.cli.report_app import report_app

# Initialize Typer CLI app and Rich console
main_app = typer.Typer(
    name="cli",
    help="Check network connectivity and generate reports - CLI or GUI",
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)

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

# --- Phase 1: Bootstrap Logging (GLOBAL, runs immediately on import) ---
# This is crucial. It ensures structlog is minimally configured BEFORE
# any other application code or Typer callbacks try to get a logger.
bootstrap_logging()


# --- Global Logger for main.py ---
# This logger will initially use the bootstrap configuration, and then
# be effectively re-configured by LoggingManagerSingleton after settings load.
# 🆕 Dynamic logger instead of static `main_logger()`
def main_logger() -> structlog.BoundLogger:
    return structlog.get_logger("main")


def _version_callback(*, value: bool = False) -> None:
    """
    Display the application version and exit.

    Args:
    ----
        value (bool): Whether to display the version.

    """
    if value:
        console.print(
            f"[bold blue]{__about__.__app_name__}[/] version: [bold green]{__about__.__version__}[/]",
        )
        sys.exit()


# --- Helper Functions for Initialization ---


def _initialize_settings_manager(config_file: Path | None) -> SettingsManager:
    """Initialize the SettingsManager Singleton and returns its instance."""
    main_logger().debug("Main callback: Initializing SettingsManager...")
    try:
        settings_manager = SettingsManagerSingleton.get_instance()
        SettingsManagerSingleton.initialize_from_context(config_path=config_file)

        main_logger().info("Main callback: SettingsManager initialized and configuration loaded.")
        for err in SettingsManagerSingleton.get_initialization_errors():
            main_logger().warning("Main callback: SettingsManager setup warning:", error_details=str(err))
        return settings_manager
    except Exception as e:
        main_logger().critical(
            "Main callback: Failed to initialize SettingsManager or load configuration!", error_details=str(e)
        )
        console.print(f"[bold red]Critical Error:[/bold red] Failed to load application configuration: {e}")
        sys.exit(1)


def _initialize_translation_manager(language: str | None, app_config: dict[str, Any]) -> TranslationManager:
    """Initialize the TranslationManager Singleton and returns its instance."""
    main_logger().debug("Main callback: Initializing TranslationManager...")
    print("Runtime TranslationManagerSingleton is from:", TranslationManagerSingleton.__module__)
    try:
        print("Debug Translation Args -- Typer START")
        print(language)
        print(app_config)
        print("Debug Translation Args -- END")
        translation_manager = TranslationManagerSingleton.get_instance()
        TranslationManagerSingleton.configure_instance(
            language=language or app_config.get("general", {}).get("default_language", "en")
        )
        main_logger().info("Main callback: TranslationManager initialized.")
        for err in TranslationManagerSingleton.get_initialization_errors():
            main_logger().warning("Main callback: TranslationManager setup warning:", error_details=str(err))
        return translation_manager
    except Exception as e:
        main_logger().critical("Main callback: Failed to initialize TranslationManager: ", error_details=str(e))
        console.print(f"[bold red]Critical Error:[/bold red] Failed to initialize translation services: {e}")
        sys.exit(1)


def _configure_logging_manager(app_context: AppContext, verbose: int, is_cli_mode: bool) -> LoggingManager:
    """Configure the LoggingManager Singleton and returns its instance."""
    main_logger().debug("Main callback: Main callback: Configuring full LoggingManager via AppContext...")

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

        main_logger().info("Main callback: Full logging configured based on application settings and CLI options.")
        for err in LoggingManagerSingleton.get_initialization_errors():
            main_logger().warning("Main callback: LoggingManager setup warning:", error_details=str(err))
        print(f"[TEST DEBUG] Logger repr after reconfig: {main_logger()}")
        print(f"[TEST DEBUG] Structlog configured: {structlog.is_configured()}")
        # Check the effective level set by the manager for testing
        # print(f"[TEST DEBUG] LoggingManager's Effective Log Level: {logging.getLevelName(logging_manager.effective_log_level)}")
        return logging_manager
    except LogHandlerError as e:
        main_logger().critical("Main callback: Critical logging setup error:", error_details=str(e))
        console.print(f"[bold red]Critical Error:[/bold red] Failed to set up core logging handlers: {e}")
        sys.exit(1)
    except Exception as e:
        main_logger().critical(
            "Main callback: Unexpected error during full logging configuration:", error_details=str(e)
        )
        console.print(f"[bold red]Critical Error:[/bold red] Unexpected error during logging setup: {e}")
        sys.exit(1)


@main_app.callback()
def main_callback(
    ctx: typer.Context,
    language: Annotated[str | None, get_language_option_definition()] = None,
    verbose: Annotated[int, get_verbose_option_definition()] = 0,
    config_file: Annotated[Path | None, get_config_option_definition()] = None,
    version: Annotated[
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

    Handle global options for the CheckConnect CLI.
    """
    main_logger().debug("Main callback: is starting!")

    main_logger().debug(
        "CLI Args",
        language=language,
        verbose=verbose,
        config_file=str(config_file) if config_file else None,
    )

    # Replicate the high-level calls from your refactored main_callback
    is_cli_mode = ctx.invoked_subcommand in ["run", "report", "summary"]
    is_gui_mode = ctx.invoked_subcommand == "gui"
    print(f"[DEBUG] CLI-Mode: {is_cli_mode}")
    print(f"[DEBUG] GUI-Mode: {is_gui_mode}")

    try:
        # --- Phase 2: Initialize SettingsManager Singleton ---
        settings_manager = _initialize_settings_manager(config_file)
        app_config = settings_manager.get_all_settings()
        print("[DEBUG Main callback] SettingsManager initialized with: ", app_config)

        # --- Phase 3: Initialize TranslationManager Singleton ---
        translation_manager = _initialize_translation_manager(language, app_config)

        # --- Phase 4: Create AppContext Instance ---
        app_context = AppContext.create(settings_instance=settings_manager, translator_instance=translation_manager)
        main_logger().debug("Main callback: AppContext created with initialized managers.")

        # --- Phase 5: Configure Full Logging via LoggingManager Singleton ---

        logging_manager = _configure_logging_manager(app_context, verbose, is_cli_mode)

        print(f"[TEST DEBUG-After-Init] Logger repr after reconfig: {main_logger()}")
        print(f"[TEST DEBUG-After-Init] Structlog configured: {structlog.is_configured()}")

        # --- Phase 6: Store parsed option values and managers in the context object for subcommands ---
        ctx.ensure_object(dict)
        if ctx.obj is None:
            ctx.obj = {}  # <--- CRITICAL: Initialize ctx.obj as a dictionary if it's None

        print(f"DEBUG: Type of ctx.obj before update: {type(ctx.obj)}")  # <--- ADD THIS
        print(f"DEBUG: Value of ctx.obj before update: {ctx.obj}")  # <--- ADD THIS

        print(f"DEBUG: SettingsManager for ctx", settings_manager)  # <--- ADD THIS
        print(f"DEBUG: AppContext for ctx", app_context)  # <--- ADD THIS

        ctx.obj.update(
            language=language,
            verbose_mode=verbose,
            config_file=config_file,
            is_cli_mode=is_cli_mode,
            is_gui_mode=is_gui_mode,
            settings_manager=SettingsManagerSingleton.get_instance(),
            translation_manager=TranslationManagerSingleton.get_instance(),
            logging_manager=logging_manager,
            app_context=app_context,  # <-- That's the problem
        )

        main_logger().debug("Main callback: All core services initialized and context prepared for subcommands.")

    except typer.Exit as e:
        print(traceback.format_exc())  # TEMPORARY
        # If an internal component or Typer itself raises typer.Exit,
        # allow it to propagate without further custom printing,
        # as it's typically already handled by Typer.
        # This is important if e.g. _version_callback raises typer.Exit
        # but your generic Exception handler above would catch it.
        raise  # Re-raise the typer.Exit exception to be handled by the runner.
    except Exception as e:
        print(traceback.format_exc())  # TEMPORARY
        # This is your custom error handling path
        critical_message = f"Critical Error: Failed to load application configuration: {e}"
        main_logger().critical(critical_message, error_details=str(e))
        console.print(f"[bold red]{critical_message}[/bold red]")  # This is your custom output

        # Instead of sys.exit(1), use typer.Exit(1)
        # This tells Typer/Click to exit gracefully with a status code,
        # which CliRunner can then capture effectively.
        raise typer.Exit(code=1)


def main() -> None:
    """Main entry point for CLI dispatch."""
    print("Starting main function")
    main_app()


if __name__ == "__main__":
    main()
