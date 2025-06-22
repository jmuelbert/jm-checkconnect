# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
The CLI run checks Module for typer.

This define the CLI for the run checks CLI.
"""

from __future__ import annotations

from pathlib import Path

import structlog
import typer

from checkconnect.cli.exceptions import ExitExceptionError
from checkconnect.config.appcontext import AppContext, initialize_app_context
from checkconnect.core.checkconnect import CheckConnect

run_app = typer.Typer(pretty_exceptions_show_locals=False)

# The 'log' variable should be retrieved AFTER the LoggingManager is configured.
# It's good practice to declare it globally if you intend to reassign it in a callback.
log: structlog.stdlib.BoundLogger # Type hint for global 'log'
# Initialize with a dummy logger or None, it will be properly set in main_callback
log = structlog.get_logger(__name__)


@run_app.command("run")
def run_command(
    ctx: typer.Context,
) -> None:
    """
    Run network tests for NTP and HTTPS servers.

    This command initializes the application context from the specified
    configuration file and language option, and then runs connectivity
    tests for both NTP servers and URLs. Results will be logged during
    the execution.

    Args:
    ----
        config_file (str): Path to the config.toml file.
        language (str): Language for the application (e.g., 'en', 'de').
        ctx (typer.Context): The Typer context object, injected automatically.

    Raises:
    ------
        ExitExceptionError: If an unexpected error occurs.
            Leave the app with typer.Exit(1)

    """
    # Retrieve global options from ctx.obj
    language: str | None = ctx.obj.get("language")
    config_file_str: str | None = ctx.obj.get("config_file") # Get string path

    log.debug(f"Run command received language: {language}, config: {config_file_str}, verbose: {verbose_mode}")

    # Prepare config_file as Path object if it's not None or empty string
    config_file_path = Path(config_file_str) if config_file_str else None


    context: AppContext = initialize_app_context(
        config_file=config_file_path,
        language=language,
    )

    log.info(context.gettext("Starting CLI in tests mode"))
    log.debug(context.gettext("Verbose logging enabled."))

    try:
        checker = CheckConnect(context=context)
        checker.run_all_checks()
    except ExitExceptionError:
        log.exception(context.gettext("Error in generate-reports."))
        typer.Exit(1)

if __name__ == "__main__":
    run_app() # Use run_app to execute
