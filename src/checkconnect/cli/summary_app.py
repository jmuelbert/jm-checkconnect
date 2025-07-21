# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
The CLI Summary Module for typer.

This define the CLI for the summary CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import structlog
import typer
from rich.console import Console

from checkconnect.exceptions import ExitExceptionError
from checkconnect.cli.options import get_data_dir_option_definition, get_report_dir_option_definition
from checkconnect.config.appcontext import AppContext
from checkconnect.reports.report_manager import OutputFormat, ReportManager
from sqlite3.dbapi2 import Date


summary_app = typer.Typer(pretty_exceptions_show_locals=False)

# The 'log' variable should be retrieved AFTER the LoggingManager is configured.
# It's good practice to declare it globally if you intend to reassign it in a callback.
log: structlog.stdlib.BoundLogger  # Type hint for global 'log'
# Initialize with a dummy logger or None, it will be properly set in main_callback
log = structlog.get_logger(__name__)


@summary_app.command("summary")
def summary(
    ctx: typer.Context,
    reports_dir: Annotated[Path | None, get_report_dir_option_definition()] = None,
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
        reports_dir (Path | None): Path to store to the last check results.
        data_dir (Path | None): Path to the data directory.
        summary_format (str): Output format for the summary ('text', 'markdown', 'html').

    Raises:
    ------
        ExitExceptionError: If an unexpected error occurs.
            Leave the app with typer.Exit(1)

    """
    # Retrieve global options from ctx.obj
    language: str | None = ctx.obj.get("language")
    config_file_str: str | None = ctx.obj.get("config_file")

    config_file_path = Path(config_file_str) if config_file_str else None

    context: AppContext = initialize_app_context(config_file=config_file_path, language=language)

    # Validate format
    valid_formats = [OutputFormat.text.value, "markdown", "html"]
    if summary_format not in valid_formats:
        msg = f"Invalid format: {summary_format}.Valid formats are: {{', '.join(valid_formats)}}"
        log.error(msg)
        raise typer.Exit(1)

    log.info(context.gettext("Generating summary..."))
    log.debug(context.gettext("Verbose logging enabled."))

    try:
        ntp_results: list[str] = []
        url_results: list[str] = []

        report_manager = ReportManager.from_params(context=context, data_dir=data_dir)

        if report_manager.results_exists():
            ntp_results, url_results = report_manager.load_previous_results()
        else:
            console.print("[bold red]No results found")
            sys.exit()

        summary_output = report_manager.get_summary(
            ntp_results,
            url_results,
            summary_format,
        )

        if summary_format == "text":
            console = Console()
            console.print(summary_output)
        else:
            typer.echo(summary_output)

    except ExitExceptionError:
        log.exception(context.gettext("Error generating summary."))
        typer.Exit(1)
