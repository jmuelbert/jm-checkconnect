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

import structlog
import typer

from checkconnect.cli.options import get_report_dir_option_definition, get_data_dir_option_definition
from checkconnect.exceptions import ExitExceptionError
from checkconnect.config.appcontext import AppContext
from checkconnect.core.checkconnect import CheckConnect
from checkconnect.reports.report_generator import ReportGenerator
from checkconnect.reports.report_manager import ReportManager

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
    log.info(app_context.gettext("Starting CLI in tests mode"))
    # The 'verbose' setting's effect on logging level is already handled by main_callback
    # so no need for specific "Verbose logging enabled" messages unless you want more nuance.
    log.debug(app_context.gettext("Debug logging is active based on verbosity setting."))

    try:
        ntp_results: list[str] = []
        url_results: list[str] = []

        report_manager = ReportManager.from_params(context=app_context, data_dir=data_dir)

        if report_manager.results_exists():
            ntp_results, url_results = report_manager.load_previous_results()
        else:
            checker = CheckConnect(context=app_context)
            checker.run_all_checks()
            ntp_results = checker.ntp_results
            url_results = checker.url_results

        report_generator = ReportGenerator.from_params(context=app_context, reports_dir=reports_dir)
        report_generator.generate_reports(
            ntp_results=ntp_results,
            url_results=url_results,
        )

    except ExitExceptionError:
        log.exception(context.gettext("Error in generate-reports mode"))
        log.error(app_context.gettext(f"Exiting due to: {e}"))
        raise typer.Exit(1)

    except Exception as e:
        log.exception(app_context.gettext("An unexpected error occurred during tests."))
        log.error(app_context.gettext(f"Exiting due to unexpected error: {e}"))
        raise typer.Exit(1)
