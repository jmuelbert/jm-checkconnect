# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2023-present Jürgen Mülbert
#

"""Main entry point for CheckConnect."""

import locale
import logging
import os
import sys
from configparser import RawConfigParser
from typing import Optional

import click
from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from checkconnect import __about__
from checkconnect.cli.main import cli_main
from checkconnect.gui.main import gui_main

# Translation setup
TRANSLATION_DOMAIN = "checkconnect"
LOCALES_PATH = os.path.join(os.path.dirname(__file__), "locales")


def get_system_locale():
    try:
        return locale.getlocale()[0] or locale.getdefaultlocale()[0]
    except:
        return "en_US"  # Fallback


def load_translation(translator, app, logger):
    """
    Loads the translation file based on the system locale.
    """
    system_locale = get_system_locale()

    # Get the locale code (e.g., "de_DE")
    locale_code = QLocale(system_locale).name()

    # Construct the translation file path
    translation_file = os.path.join(LOCALES_PATH, f"checkconnect_{locale_code}.qm")

    if os.path.exists(translation_file):
        # Load the translation file
        translator.load(translation_file)

        # Install the translator
        app.installTranslator(translator)
        logger.info(f"Translation loaded for locale: {locale_code}")
        return translator
    else:
        logger.warning(f"Translation file not found for locale: {locale_code}")
    return None  # Return none if not load and used the identity function


@click.command()
@click.option("--gui", is_flag=True, help="Start the GUI version")
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True),
    help="Path to the configuration file",
    default="config.ini",
)
@click.option("-o", "--output", type=click.Path(), help="Path to the output file")
@click.option("-v", "--verbose", is_flag=True, help="Enable detailed logs")
@click.option(
    "--version",
    is_flag=True,
    help="Show the version and exit.",
)  # Added version option
def main(gui: bool, config: str, output: str, verbose: bool, version: bool):
    """
    Main function for CheckConnect.

    This function sets up logging and decides whether to run
    the CLI or GUI version of CheckConnect based on user input.

    Args:
    ----
        gui (bool):  A flag indicating whether to start the GUI version.
        config (str):  The path to the configuration file.
        output (str):  The path to the output file.
        verbose (bool):  A flag indicating whether to enable detailed logs.
        version (bool): A flag indicating whether to show the version and exit.

    """
    # Load configuration from file
    config_parser = RawConfigParser()
    config_parser.read(config)

    # Configure logging based on verbosity flag and config file
    log_level_str = config_parser.get("Logging", "level", fallback="INFO").upper()
    log_level = getattr(
        logging,
        log_level_str,
        logging.INFO,
    )  # Convert string to logging level
    if verbose:
        log_level = logging.DEBUG

    # Get handler configurations
    console_handler_level_str = config_parser.get(
        "Logging",
        "console_handler_level",
        fallback="DEBUG",
    ).upper()
    console_handler_level = getattr(logging, console_handler_level_str, logging.DEBUG)
    file_handler_level_str = config_parser.get(
        "Logging",
        "file_handler_level",
        fallback="INFO",
    ).upper()
    file_handler_level = getattr(logging, file_handler_level_str, logging.INFO)

    file_handler_file = config_parser.get(
        "Logging",
        "file_handler_file",
        fallback="checkconnect.log",
    )  # Get log file name

    # Get formatter configuration
    formatter_format = config_parser.get(
        "Logging",
        "simple_formatter_format",
        fallback="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    formatter_datefmt = config_parser.get(
        "Logging",
        "simple_formatter_datefmt",
        fallback="",
    )

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=formatter_format,
        datefmt=formatter_datefmt,
        filename=file_handler_file,
    )  # set filename

    logger = logging.getLogger("CheckConnect")
    logger.info(f"Starting CheckConnect Version: {__about__.__version__}")

    # Translation setup
    translator = QTranslator()
    app = None  # Define early
    # Determine execution mode
    if gui:
        # Load translation
        app = QApplication(sys.argv)
        translation = load_translation(
            translator,
            app,
            logger,
        )  # Load and apply translation
        logger.info("Launching GUI mode")
        gui_main(config_parser, output, logger)  # Pass config parser to GUI
        sys.exit(app.exec())
    else:
        logger.info("Launching CLI mode")
        cli_main(config_parser, output)  # Pass config parser to CLI


# Run the main function when the script is executed directly
if __name__ == "__main__":
    main()
