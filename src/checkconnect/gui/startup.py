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

if TYPE_CHECKING:
    from collections.abc import Callable

# Conditional import for type checking, as AppContext is only needed for type hints here.
# The actual AppContext instance is passed at runtime.
if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext

log = structlog.get_logger(__name__)


def _try_load_translation(
    path: str, qt_translator: QTranslator, app: QApplication, translate: Callable[[str], str]
) -> bool:
    """
    Attempts to load and install a Qt translation from the given path.

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
            msg = translate(f"Loaded Qt translations from Qt resource: {path}")
        else:
            msg = translate(f"Loaded Qt translations from file: {path}")
        log.info(msg)
        return True
    return False


def setup_translations(
    app: QApplication,
    context: AppContext,
    language: str | None = None,
    translations_dir: Path | None = None,
) -> None:
    """
    Sets up and installs Qt translations for the application.

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
            msg = translate(f"Using Qt preferred UI language for translations: {language} (from {ui_languages[0]})")
            log.info(msg)
        else:
            # Fallback to system locale name if UI languages are not available
            language = QLocale.system().name().split("_")[0]
            msg = translate(f"Qt preferred UI languages not found, falling back to system locale: {language}")
            log.warning(msg)

    attempted_paths = [
        f":/translations/{language}.qm",
        str((translations_dir or Path(user_data_dir(__about__.__app_name__)) / "translations") / f"{language}.qm"),
    ]

    for path in attempted_paths:
        if _try_load_translation(path, qt_translator, app, translate):
            return

    msg = translate(f"No Qt translation found for language '{language}'")
    log.warning(msg)


def run(context: AppContext, language: str | None = None) -> None:
    """
    Initializes and runs the CheckConnect GUI application.

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
    """
    # Check if a QApplication instance already exists to prevent
    # "QApplication: An instance of QApplication already exists." errors.
    #
    translate = context.translator.translate

    app = QApplication.instance()
    created_new_app = False

    if app is None:
        # Create a new QApplication only if one doesn't already exist.
        app = QApplication(sys.argv)
        created_new_app = True
        log.debug(translate("New QApplication instance created."))
    else:
        log.debug(translate("Using existing QApplication instance."))

    exit_code = 0
    try:
        # The 'context' object should contain the default language config from TOML
        # if not explicitly passed to this function.

        # Load Qt translations based on the provided language or system locale.
        setup_translations(app=app, context=context, language=language)

        # Import CheckConnectGUI here to avoid circular dependencies if it
        # directly or indirectly imports this module.
        from checkconnect.gui.gui_main import CheckConnectGUIRunner

        # Create and show the main GUI window.
        window = CheckConnectGUIRunner(context=context)

        # Show and run event loop
        window.show()
        log.info(translate("CheckConnect GUI window displayed."))

        # Start the Qt event loop. This blocks until the application exits.
        exit_code = app.exec()
        msg = translate(f"Qt application exited with code: {exit_code}")
        log.info(msg)

    except Exception as e:
        # Catch any unexpected errors during GUI initialization or execution.
        msg = translate(f"Failed to close GUI window cleanly: {e}")
        log.exception(msg)
        exit_code = 1
    finally:
        # Ensure window is closed if it was created
        if "window" in locals() and window:
            try:
                window.close()
                log.debug(translate("CheckConnect GUI window closed."))
            except Exception as e:  # noqa: BLE001
                msg = translate(f"Failed to close GUI window cleanly: {e}")
                log.warning(msg)

        if created_new_app:
            # Ensure the QApplication is quit even on error if we created it.
            app.quit()
            log.debug(translate("QApplication instance quit."))

        sys.exit(exit_code)
