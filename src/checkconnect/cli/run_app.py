# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
The CLI run checks Module for typer.

This define the CLI for the run checks CLI.
"""

from __future__ import annotations

import structlog
import typer

from checkconnect.exceptions import ExitExceptionError
from checkconnect.config.appcontext import AppContext  # Import the revised AppContext
from checkconnect.core.checkconnect import CheckConnect

run_app = typer.Typer(pretty_exceptions_show_locals=False)

# The 'log' variable should be retrieved AFTER the LoggingManager is configured.
# It's good practice to declare it globally if you intend to reassign it in a callback.
log: structlog.stdlib.BoundLogger  # Type hint for global 'log'
# Initialize with a dummy logger or None, it will be properly set in main_callback
log = structlog.get_logger(__name__)


@run_app.command("run")
def run_command(ctx: typer.Context) -> None:
    """
    Run network tests for NTP and HTTPS servers.

    This command uses the globally initialized application context, including
    settings and logging, to run connectivity tests.

    Args:
    ----
        ctx (typer.Context): The Typer context object, injected automatically.

    Raises:
    ------
        ExitExceptionError: If a specific application-level error occurs during checks.
                            This will typically cause a clean exit with a message.
        typer.Exit(1): For unhandled exceptions leading to an abnormal termination.
    """
    # Retrieve the AppContext instance from ctx.obj
    # This AppContext instance is already initialized with SettingsManager,
    # LoggingManager (which has configured global structlog), and TranslationManager.
    app_context: AppContext = ctx.obj["app_context"]

    print(f"[DEBUG typer-run_app] AppContext from ctx: {app_context}")

    # Now, use the AppContext to access services
    log.info(app_context.gettext("Starting CLI in tests mode"))
    # The 'verbose' setting's effect on logging level is already handled by main_callback
    # so no need for specific "Verbose logging enabled" messages unless you want more nuance.
    log.debug(app_context.gettext("Debug logging is active based on verbosity setting."))

    try:
        # CheckConnect should now take the AppContext instance
        checker = CheckConnect(context=app_context)
        checker.run_all_checks()
    except ExitExceptionError as e:
        log.exception(app_context.gettext("Error in run_command."))
        sys.exit(1)
        raise typer.Exit(1)
    except Exception as e:
        log.exception(app_context.gettext("An unexpected error occurred during tests."))
        sys.exit(1)
        raise typer.Exit(1)


if __name__ == "__main__":
    run_app()  # Use run_app to execute
