# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Run CheckConnect in graphical user interface (GUI) mode.

This function initializes the application context, logging, and translations,
then creates and shows the main application window. It handles lifecycle
management
"""

from __future__ import annotations

import structlog
import typer
from rich.console import Console

from checkconnect.exceptions import ExitExceptionError
from checkconnect.config.appcontext import AppContext
from checkconnect.gui import startup


console = Console()

gui_app = typer.Typer(pretty_exceptions_show_locals=False)

# The 'log' variable should be retrieved AFTER the LoggingManager is configured.
# It's good practice to declare it globally if you intend to reassign it in a callback.
log: structlog.stdlib.BoundLogger  # Type hint for global 'log'
# Initialize with a dummy logger or None, it will be properly set in main_callback
log = structlog.get_logger(__name__)


@gui_app.command("gui")
def gui(ctx: typer.Context) -> None:
    """
    Run CheckConnect in graphical user interface (GUI) mode.

    This function retrieves the pre-initialized application context,
    then creates and shows the main application window. It handles lifecycle
    management of the GUI framework and exits with the appropriate status code.

    Args:
    ----
        ctx (typer.Context): The Typer context object, injected automatically.

    Exits:
        The application exits with code 0 on success, or 1 on failure.

    """
    # Retrieve the AppContext instance from ctx.obj
    # This AppContext instance is already initialized with SettingsManager,
    # LoggingManager (which has configured global structlog), and TranslationManager.
    app_context: AppContext = ctx.obj["app_context"]
    language = ctx.obj["language"]

    # Now, use the app_context for all shared services
    log.info(app_context.gettext("Starting CheckConnect GUI..."))
    # The 'verbose' setting's effect on logging level is already handled by main_callback
    # so no need for specific "Verbose logging enabled" messages unless you want more nuance.
    log.debug(app_context.gettext("Debug logging is active based on verbosity setting."))

    try:
        # Pass the app_context to your GUI startup function.
        # This function should then use app_context.settings, app_context.gettext,
        # and app_context.get_module_logger to build and run the GUI.
        startup.run(context=app_context, language=language)

        # IMPORTANT: If checkconnect.gui.startup.run initiates a blocking GUI event loop
        # (like QApplication.exec_() or root.mainloop()),
        # this function will block until the GUI closes.
        # If it returns, it implies the GUI has shut down.

    except ExitExceptionError as e:
        # Catch specific application-level GUI errors that should lead to an explicit exit
        console.print(f"[bold red]Critical Error:[/bold red] Cannot start GUI due to application error:{e}")
        log.exception(app_context.gettext(f"Cannot start GUI due to application error: {e}"))
        raise typer.Exit(1)
    except Exception as e:
        # Catch any other unexpected errors during GUI startup or lifecycle
        console.print(f"[bold red]Critical Error:[/bold red] Cannot start GUI due to application error:{e}")
        log.exception(app_context.gettext(f"An unexpected error occurred during GUI startup: {e}"))
        raise typer.Exit(1)


if __name__ == "__main__":
    # This block is typically for testing the subcommand in isolation.
    # In a real app, `main_app()` in your root main.py will dispatch to this.
    gui_app()
