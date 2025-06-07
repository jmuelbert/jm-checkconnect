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
from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext


log = structlog.get_logger(__name__)

def setup_translations(
    app: QApplication,
    context: AppContext,
    language: str | None = None,
    translations_dir: Path | None = None,
) -> None:
    """
    Setup translations.

    Load and install Qt translations in the following order:
    1. From Qt resource (e.g., `:/translations/en.qm`)
    2. From local filesystem (default `translations/` folder)
    3. From fallback absolute file path

    Args:
    ----
        app: The QApplication instance
        context: The Application Context
        logger: Logger instance
        language: Language code (e.g., "en")
        translations_dir: Optional directory to search for translations

    """
    translate = context.translator.translate
    qt_translator = QTranslator()

    if not language:
        # Actual system locale
        language: str = QLocale.system().name()
        context.translator.set_language(language)

    # First try loading from resource
    resource_path = f":/translations/{language}.qm"

    if qt_translator.load(resource_path):
        app.installTranslator(qt_translator)
        msg = translate(f"Qt translations loaded from resource: {resource_path}")
        log.info(msg)
        return

    # If resource loading failed, try filesystem
    msg = translate(f"Could not load Qt translations from resource: {resource_path}")
    log.warning(msg)

    # Try filesystem path
    translations_path = Path(__file__).resolve().parent / "translations"
    file_path = translations_path / f"{language}.qm"

    # Use default translations path if none provided
    if translations_dir is None:
        translations_dir = Path(__file__).resolve().parent / "translations"

    file_path = translations_dir / f"{language}.qm"
    if file_path.exists() and qt_translator.load(str(file_path)):
        app.installTranslator(qt_translator)
        msg = translate(f"Qt translations loaded from file: {file_path}")
        log.info(msg)
        return

    msg = f"Translation file not found or failed to load: {file_path}"
    log.warning(msg)

    # Fallback absolute path string (for edge cases)
    fallback_file = translations_dir.joinpath(f"{language}.qm")
    if fallback_file.exists():
        try:
            if qt_translator.load(str(fallback_file)):
                app.installTranslator(qt_translator)
                msg = translate(
                    f"Qt translations loaded from fallback: {fallback_file}",
                )
                log.info(msg)
                return
        except Exception as e:
            msg = translate(f"Error loading fallback translation file: {e}")
            log.exception(msg)


def run(
    context: AppContext,
    language: str | None = None
) -> None:
    # Check if QApplication already exists
    app = QApplication.instance()
    created_new_app = False

    if app is None:
        # Create new QApplication only if one doesn't already exist
        app = QApplication(sys.argv)
        created_new_app = True

    try:
        # fallback to TOML default

        # Load Qt translations
        if language:
            setup_translations(app, context, language)
        else:
            setup_translations(app, context)

        # Create and show the main GUI window
        window = CheckConnectGUI(context=context)
        window.show()

        # Start the event loop
        exit_code: int = app.exec()

        # Clean up on exit
        window.close()

        if created_new_app:
            app.quit()

        sys.exit(exit_code)

    except Exception as e:
        msg = context.gettext(f"Error during GUI initialization: {e}")
        log.exception(msg)
        if created_new_app:
            app.quit()
        sys.exit(1)
