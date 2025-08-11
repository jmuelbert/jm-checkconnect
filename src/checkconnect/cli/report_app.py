# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Generate HTML and PDF reports from the most recent connectivity test results.

This command generates both HTML and PDF reports based on the results
of the latest NTP and URL tests. The reports are saved in the specified
output directory. If no results are available, an error is logged.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import structlog
import typer
from rich.console import Console

from checkconnect.cli.options import get_data_dir_option_definition, get_report_dir_option_definition
from checkconnect.core.checkconnect import CheckConnect
from checkconnect.exceptions import ExitExceptionError
from checkconnect.reports.report_generator import ReportGenerator
from checkconnect.reports.report_manager import ReportManager

if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext

console = Console()

report_app = typer.Typer(pretty_exceptions_show_locals=False)

# The 'log' variable should be retrieved AFTER the LoggingManager is configured.
# It's good practice to declare it globally if you intend to reassign it in a callback.
log: structlog.stdlib.BoundLogger  # Type hint for global 'log'
# Initialize with a dummy logger or None, it will be properly set in main_callback
log = structlog.get_logger(__name__)


@report_app.command("report")
def reports(
    ctx: typer.Context,
    data_dir: Annotated[Path | None, get_data_dir_option_definition()] = None,
    reports_dir: Annotated[Path | None, get_report_dir_option_definition()] = None,
) -> None:
    """
    Generate HTML and PDF reports from the most recent connectivity test results.

    This command generates both HTML and PDF reports based on the results
    of the latest NTP and URL tests. The reports are saved in the specified
    output directory. If no results are available, an error is logged.

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
    log.info(app_context.gettext("Starting Checkconnect in generate-reports mode."))
    # The 'verbose' setting's effect on logging level is already handled by main_callback
    # so no need for specific "Verbose logging enabled" messages unless you want more nuance.
    log.debug(app_context.gettext("Debug logging is active based on verbosity setting."))

    try:
        ntp_results: list[str] = []
        url_results: list[str] = []

        console.print(app_context.gettext("[bold green]Generating reports.[/bold green]"))

        report_generator = ReportGenerator.from_params(context=app_context, arg_reports_dir=reports_dir)
        report_manager = ReportManager.from_params(context=app_context, arg_data_dir=data_dir)

        if report_manager.results_exists():
            ntp_results, url_results = report_manager.load_previous_results()
        else:
            checker = CheckConnect(context=app_context)
            checker.run_all_checks()
            ntp_results = checker.ntp_results
            url_results = checker.url_results


        report_generator.generate_reports(
            ntp_results=ntp_results,
            url_results=url_results,
        )

        console.print(app_context.gettext("[bold green]Reports generated successfully[/bold green]"))

    except ExitExceptionError as e:
        console.print(
            app_context.gettext(
                f"[bold red]Critical Error:[/bold red] Cannot start generate reports for checkconnect. ({e})"
            )
        )
        log.exception(app_context.gettext("Cannot start generate reports for checkconnect error."), exc_info=e)
        raise typer.Exit(1) from e

    except Exception as e:
        console.print(
            app_context.gettext(
                f"[bold red]Critical Error:[/bold red] An unexpected error occurred generate reports. ({e})"
            )
        )
        log.exception(app_context.gettext("An unexpected error occurred generate reports."), exc_info=e)
        raise typer.Exit(1) from e
