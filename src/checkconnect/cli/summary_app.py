# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
The CLI Summary Module for typer.

This define the CLI for the summary CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import structlog
import typer
from rich.console import Console

from checkconnect.cli.options import get_data_dir_option_definition
from checkconnect.exceptions import ExitExceptionError
from checkconnect.reports.report_manager import OutputFormat, ReportManager

if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext

console = Console()

summary_app = typer.Typer(pretty_exceptions_show_locals=False)

# The 'log' variable should be retrieved AFTER the LoggingManager is configured.
# It's good practice to declare it globally if you intend to reassign it in a callback.
log: structlog.stdlib.BoundLogger  # Type hint for global 'log'
# Initialize with a dummy logger or None, it will be properly set in main_callback
log = structlog.get_logger(__name__)


@summary_app.command("summary")
def summary(
    ctx: typer.Context,
    data_dir: Annotated[Path | None, get_data_dir_option_definition()] = None,
    summary_format: Annotated[
        OutputFormat,
        typer.Option(
            ...,
            "--format",
            "-f",
            case_sensitive=False,
            help="Output format: text, markdown, html.",
            rich_help_panel="Configuration",
        ),
    ] = OutputFormat.text,
) -> None:
    """
    Generate a summary of the most recent connectivity test results.

    The summary includes the latest NTP and URL test results and is
    displayed in the specified format (text, markdown, or HTML).
    If no results are available, an error is logged.

    Args:
    ----
        ctx (typer.Context): The Typer context object, injected automatically.


    Raises:
    ------
        ExitExceptionError: If an unexpected error occurs.
            Leave the app with typer.Exit(1)

    """
    # Retrieve the AppContext instance from ctx.obj
    # This AppContext instance is already initialized with SettingsManager,
    # LoggingManager (which has configured global structlog), and TranslationManager.
    app_context: AppContext = ctx.obj["app_context"]

    # Now, use the AppContext to access services
    log.info(app_context.gettext("Starting Checkconnect in summary mode."))
    # The 'verbose' setting's effect on logging level is already handled by main_callback
    # so no need for specific "Verbose logging enabled" messages unless you want more nuance.
    log.debug(app_context.gettext("Debug logging is active based on verbosity setting."))

    # Validate format
    valid_formats = [OutputFormat.text.value, "markdown", "html"]
    if summary_format not in valid_formats:
        msg = app_context.gettext("Invalid format: {summary_format}.Valid formats are: {{', '.join(valid_formats)}}")
        log.error(msg)
        raise typer.Exit(1)

    try:
        ntp_results: list[str] = []
        url_results: list[str] = []

        report_manager = ReportManager.from_params(context=app_context, arg_data_dir=data_dir)

        if report_manager.results_exists():
            ntp_results, url_results = report_manager.load_previous_results()
        else:
            console.print("[bold red]Error:[/bold red] No saved result found.")
            sys.exit(1)

        summary_output = report_manager.get_summary(
            ntp_results=ntp_results,
            url_results=url_results,
            summary_format=summary_format,
        )

        console.print(app_context.gettext("[bold green]Results:[/bold green]"))
        if summary_format == "text":
            console.print(summary_output)
        else:
            typer.echo(summary_output)

    except ExitExceptionError as e:
        console.print(
            app_context.gettext(f"[bold red]Error:[/bold red] Cannot start generate summary for checkconnect. ({e})")
        )
        log.exception(app_context.gettext("Cannot start generate summary for checkconnect."), exc_info=e)
        raise typer.Exit(1) from e

    except Exception as e:
        console.print(
            app_context.gettext(f"[bold red]Error:[/bold red] An unexpected error occurred generate summary. ({e})")
        )
        log.exception(app_context.gettext("An unexpected error occurred generate summary."), exc_info=e)
        raise typer.Exit(1) from e
