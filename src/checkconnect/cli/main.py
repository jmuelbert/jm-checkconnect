# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Main entry point for the CheckConnect application.

This script dispatches between the command-line interface (CLI) and
the graphical user interface (GUI), based on the selected mode.
"""

from __future__ import annotations

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

# from checkconnect.cli.gui_app import gui_app
# from checkconnect.cli.report_app import report_app
from checkconnect.cli.run_app import run_app
from checkconnect.config.logging_manager import LoggingManagerSingleton

# Define log levels based on verbosity count
VERBOSITY_LEVELS = {
    0: logging.INFO,    # Default, no -v
    1: logging.DEBUG,   # -v
    2: logging.NOTSET   # -vv (or even lower if you have TRACE etc.)
}
console = Console()

# Initialize Typer CLI app and Rich console
main_app = typer.Typer(
    name="cli",
    help="Check network connectivity and generate reports - CLI or GUI",
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)

main_app.add_typer(
    run_app,
    help=f"Run {__about__.__app_name__} in CLI mode (run tests).",
)

# main_app.add_typer(
#     report_app,
#     help=f"Run {__about__.__app_name__} in CLI mode (generate reports).",
# )

# main_app.add_typer(
#     summary_app,
#     help=f"Run {__about__.__app_name__} in CLI mode (show summary).",
# )

# main_app.add_typer(
#     gui_app,
#     help=f"Run {__about__.__app_name__} in GUI mode.",
# )


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


@main_app.callback()
def main_callback(
    ctx: typer.Context,
    language: Annotated[str | None, get_language_option_definition()] = None,  # Use the function to get the Option
    verbose: Annotated[int, get_verbose_option_definition()] = 0,
    config_file: Annotated[str | None, get_config_option_definition()] = None,
    version: Annotated[
        bool | None,  # Keep Optional[bool] as it's common for --version flags that exit
        typer.Option(
            # Crucial: Start with the flag name(s) directly, not 'None'.
            # The 'default' will be handled by the '=None' in the signature.
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,  # Keep the default value her,
) -> None:
    """
    CheckConnect is a CLI tool for network connectivity checks.

    Handle global options for the CheckConnect CLI.
    """
    # 1: Explicitly check for CLI commands vs. GUI commands
    is_cli_mode = ctx.invoked_subcommand in ["run", "report", "summary"] # Add other CLI commands here
    is_gui_mode = ctx.invoked_subcommand == "gui" # Add other GUI commands if any

    # You can pass language and verbose to the commands if needed
    # 2. Configure Logging based on verbose
    cli_log_level = VERBOSITY_LEVELS.get(verbose, logging.DEBUG)
    logging_manager = LoggingManagerSingleton.get_instance(cli_log_level=cli_log_level, enable_console_logging=is_cli_mode)
    global log
    log = logging_manager.get_logger(__name__)  # Reconfigure global log for main_app

    log.debug("Main callback: Global options processed and logging initialized.")

    # 3. Store parsed option values in the context object for subcommands
    ctx.ensure_object(dict)  # Ensure ctx.obj exists as a dict
    ctx.obj["language"] = language
    ctx.obj["verbose_mode"] = verbose
    ctx.obj["config_file"] = config_file  # Store config_file string
    # Store the mode information in the context as well if subcommands might need it
    ctx.obj["is_cli_mode"] = is_cli_mode
    ctx.obj["is_gui_mode"] = is_gui_mode

def main() -> None:
    """Main entry point for CLI dispatch."""
    main_app()


if __name__ == "__main__":
    main()
