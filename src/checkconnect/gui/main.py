# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
GUI entry point for CheckConnect.

This module serves as the main entry for the GUI version of CheckConnect.
"""

import configparser
import gettext
import importlib
import locale
import logging
import os
import sys
from typing import Optional

from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from checkconnect.gui.checkconnect_gui import CheckConnectGUI

# Define the translation domain
TRANSLATION_DOMAIN = "checkconnect"

# Set the locales path relative to the current file
LOCALES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "gui",
    "locales",
)


# Function to get the current locale
def get_system_locale():
    try:
        return locale.getlocale()[0] or locale.getdefaultlocale()[0]
    except:
        return "en_US"  # Fallback


# Use it for logger names

logger = logging.getLogger(__name__)  # Get logger for this module


def gui_main(
    config_parser: configparser.ConfigParser,
    output_file: Optional[str] = None,
    logger: logging.Logger = None,
):
    """
    Main function for launching the CheckConnect GUI.

    This function initializes the logging configuration, creates an instance of
    the CheckConnectGUI class, and starts the GUI application.

    Args:
    ----
        config_parser (configparser.ConfigParser):  The configuration parser containing the settings for the application.
        output_file (Optional[str], optional):  The path to the output file for test results.  Defaults to None.
        logger (logging.Logger, optional): A logger instance. If None, a default logger is created.

    """
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info("Starting CheckConnect GUI...")

    # Check if QApplication already exists
    app = QApplication.instance()
    if app is None:
        # Create new QApplication only if one doesn't already exist
        app = QApplication(sys.argv)
        created_new_app = True
    else:
        # Use existing QApplication
        created_new_app = False

    translator = QTranslator()  # Create the Translator

    # Load Translation
    system_locale = get_system_locale()

    # Get the locale code (e.g., "de_DE")
    locale_code = QLocale(system_locale).name()

    # Construct the translation file path
    translations_path = str(
        importlib.resources.files("checkconnect") / "gui/translations",
    )

    if translator.load(f"{translations_path}/{locale}.qm"):
        # Install the translator
        app.installTranslator(translator)
        logger.debug(f"Translation loaded for locale: {locale_code}")
    else:
        logger.warning(f"Translation file not found for locale: {locale_code}")

    window = CheckConnectGUI(
        config_parser,
        output_file,
        logger=logger,
    )  # inject also this logger!
    window.show()

    exit_code = app.exec()  # Run the application event loop

    # Clean up and exit
    window.close()  # Close the window

    # Only quit if we created the app
    if created_new_app:
        app.quit()  # Quit the application

    sys.exit(exit_code)
