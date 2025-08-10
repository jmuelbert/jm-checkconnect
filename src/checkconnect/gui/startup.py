# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
GUI entry point for CheckConnect.

This module initializes and launches the CheckConnect GUI application. It sets up the
application context, logging, and translations before displaying the main window.
The Qt event loop is started and terminated appropriately.

The GUI mode is an alternative to the CLI for users who prefer a graphical interface.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from platformdirs import user_data_dir
from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from checkconnect import __about__
from checkconnect.gui.gui_main import CheckConnectGUIRunner

if TYPE_CHECKING:
    from collections.abc import Callable

# Conditional import for type checking, as AppContext is only needed for type hints here.
# The actual AppContext instance is passed at runtime.
if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)

def _try_load_translation(
    path: str, qt_translator: QTranslator, app: QApplication, translate: Callable[[str], str]
) -> bool:
    """
    Attempt to load and install a Qt translation from the given path.

    Args:
        path (str): The path to the `.qm` translation file.
        qt_translator (QTranslator): The translator instance to use.
        app (QApplication): The current application instance.
        translate (Callable[[str], str]): Translation function for logging messages.

    Returns:
        bool: True if the translation was successfully loaded and installed, False otherwise.
    """
    if qt_translator.load(path):
        app.installTranslator(qt_translator)
        if path.startswith(":/"):
            msg = translate("Loaded Qt translations from Qt resource.")
        else:
            msg = translate("Loaded Qt translations from file.")
        log.debug(msg, path=str(path))
        return True
    return False


def setup_translations(
    app: QApplication,
    context: AppContext,
    language: str | None = None,
    translations_dir: Path | None = None,
) -> None:
    """
    Set up and installs Qt translations for the application.

    This function attempts to load Qt translation files (`.qm` files) from
    several locations in a specific order:
    1. From Qt resources (e.g., embedded in the executable via Qt's resource system).
    2. From a local 'translations/' directory relative to the script's location.
    3. From a fallback absolute file path, if a specific `translations_dir` is provided.

    If no `language` is specified, the system's current locale is used.
    A successful translation load installs the `QTranslator` onto the `QApplication`.
    Informative messages are logged at various stages of the process.

    Args:
        app (QApplication): The main QApplication instance for the GUI application.
        context (AppContext): The application context, providing access to
                              the translator and logger.
        language (str | None): Optional. The language code (e.g., "en", "de")
                               to load translations for. If None, the system locale is used.
        translations_dir (Path | None): Optional. A specific directory path to
                                        search for translation files. If None,
                                        a default relative path is used.
    """
    # Access the translate function from the application context's translator.
    translate = context.translator.translate
    qt_translator = QTranslator()

    if not language:
        # Get the preferred UI languages list from Qt
        ui_languages = QLocale.system().uiLanguages()
        if ui_languages:
            # Use the first preferred language as the base language for your app
            # QLocale.system().uiLanguages() might return 'de-DE', 'en-US', etc.
            # You usually want the 'de' or 'en' part.
            language = ui_languages[0].split("-")[0]
            log.debug(translate("Using Qt preferred UI language for translations"),
                language=language,
                ui_language=ui_languages[0])
        else:
            # Fallback to system locale name if UI languages are not available
            language = QLocale.system().name().split("_")[0]
            log.warning(translate("Qt preferred UI languages not found, falling back to system locale."),
                language=language)

    attempted_paths = [
        f":/translations/{language}.qm",
        str((translations_dir or Path(user_data_dir(__about__.__app_name__.lower())) / "translations") / f"{language}.qm"),
    ]

    for path in attempted_paths:
        if _try_load_translation(path, qt_translator, app, translate):
            return

    log.warning(translate("No Qt translation found for language."),
        language=language)


def run(context: AppContext, language: str | None = None) -> int:
    """
    Initialize and runs the CheckConnect GUI application.

    This function manages the lifecycle of the Qt application. It checks if a
    QApplication instance already exists (e.g., in a test environment) and creates
    one if necessary. It then sets up logging and translations, creates the main GUI
    window, shows it, and starts the Qt event loop. Proper cleanup is performed
    upon application exit.

    Args:
        context (AppContext): The application context, providing configurations,
                              logging, and other shared services.
        language (str | None): Optional. The language code to use for the GUI,
                               overriding the system default if provided.

    Returns:
        int: The exit code of the Qt application.
    """
    # Check if a QApplication instance already exists to prevent
    # "QApplication: An instance of QApplication already exists." errors.
    #
    translate = context.translator.translate

    app = QApplication.instance()
    created_new_app = False
    window = None

    if app is None:
        # Create a new QApplication only if one doesn't already exist.
        app = QApplication(sys.argv)
        created_new_app = True
        log.debug(translate("New QApplication instance created."))
    else:
        log.debug(translate("Using existing QApplication instance."))

    exit_code = 1 # Default to an error code

    try:
        # The 'context' object should contain the default language config from TOML
        # if not explicitly passed to this function.

        # Load Qt translations based on the provided language or system locale.
        setup_translations(app=app, context=context, language=language)

        # Create and show the main GUI window.
        window = CheckConnectGUIRunner(context=context)

        # Show and run event loop
        window.show()
        log.info(translate("CheckConnect GUI window displayed."))

        # Start the Qt event loop. This blocks until the application exits.
        exit_code = app.exec()
        log.info(translate("Qt application exited with code."), exit_code=exit_code)

    except Exception as e:
        # Catch any unexpected errors during GUI initialization or execution.
        log.exception(translate("Failed to close GUI window cleanly."), exc_info=e)
        exit_code = 1

    finally:
        # Ensure window is closed if it was created
        if window:
            try:
                window.close()
                log.debug(translate("CheckConnect GUI window closed."))
            except Exception as e:
                log.exception(translate("Failed to close GUI window cleanly."), exc_info=e)
                # The exit_code is already 1 from the exception, no need to re-assig

        # Only quit the QApplication if we created it
        if created_new_app:
            # Ensure the QApplication is quit even on error if we created it.
            log.debug(translate("QApplication instance quit."))
            app.quit()

    return exit_code

if __name__ == "__main__":
    # This is how the function is typically called.
    # The responsibility of calling sys.exit() is now on the caller.
    # sys.exit(run(context=...))
    pass
