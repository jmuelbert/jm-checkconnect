# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Generate HTML and PDF reports from the most recent connectivity test results.

This command generates both HTML and PDF reports based on the results
of the latest NTP and URL tests. The reports are saved in the specified
output directory. If no results are available, an error is logged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated
from rich.console import Console
import structlog
import typer

from checkconnect.cli.options import get_report_dir_option_definition, get_data_dir_option_definition
from checkconnect.exceptions import ExitExceptionError
from checkconnect.config.appcontext import AppContext
from checkconnect.core.checkconnect import CheckConnect
from checkconnect.reports.report_generator import ReportGenerator
from checkconnect.reports.report_manager import ReportManager

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

        report_manager = ReportManager.from_params(context=app_context, arg_data_dir=data_dir)

        if report_manager.results_exists():
            print("[DEBUG Report-App] Loading previous results...")
            ntp_results, url_results = report_manager.load_previous_results()
        else:
            print("[DEBUG Report-App] Generating reports with CheckConnect.")
            checker = CheckConnect(context=app_context)
            checker.run_all_checks()
            print("[DEBUG Report-App] Getting results from CheckConnect")
            ntp_results = checker.get_ntp_results()
            url_results = checker.get_url_results()

        report_generator = ReportGenerator.from_params(context=app_context, arg_reports_dir=reports_dir)
        print(f"[DEBUG Report-App] Generating reports with ntp_results={ntp_results} and url_results={url_results}")
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
        log.exception(app_context.gettext(f"Cannot start generate reports for checkconnect error: {e}"))
        raise typer.Exit(1)

    except Exception as e:
        console.print(
            app_context.gettext(
                f"[bold red]Critical Error:[/bold red] An unexpected error occurred generate reports. ({e})"
            )
        )
        log.exception(app_context.gettext(f"An unexpected error occurred generate reports error:{e}"))
        raise typer.Exit(1)
