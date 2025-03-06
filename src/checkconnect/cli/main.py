# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Main entry point for the CLI.

This script initializes the CLI mode for the CheckConnect application.
It performs connectivity tests for NTP servers and URLs and generates reports.
"""

import configparser
import gettext
import logging
import os
from typing import Optional

from checkconnect.cli.checkconnect import CheckConnect

# Define the translation domain
TRANSLATION_DOMAIN = "checkconnect"

# Set the locales path relative to the current file
LOCALES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "cli",
    "locales",
)


# Initialize gettext
try:
    translate = gettext.translation(
        TRANSLATION_DOMAIN,
        LOCALES_PATH,
        languages=[os.environ.get("LANG", "en")],  # Respect the system language
    ).gettext
except FileNotFoundError:
    # Fallback to the default English translation if the locale is not found
    def translate(message):
        return message


class CLIMain:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run(self, config_parser: configparser.ConfigParser, output_file: Optional[str]):
        """
        Main function for the CLI.

        This function:
        - Creates an instance of CheckConnect with the configuration and output file.
        - Runs the CheckConnect application.

        Args:
        ----
            config_parser (configparser.ConfigParser): The configuration parser containing the settings.
            output_file (Optional[str]): The path to the output file.  If None, output will only be logged.

        """
        self.logger.info(translate("Running CheckConnect in CLI mode"))

        try:
            check_connect = CheckConnect(
                config_parser,
                output_file,
            )  # Pass config parser
            check_connect.run()
            check_connect.generate_reports()
            self.logger.info(translate("Reports have been generated."))
        except Exception as e:
            self.logger.exception(
                translate(f"An error occurred during CLI execution: {e}"),
            )


def cli_main(config_parser: configparser.ConfigParser, output_file: Optional[str]):
    """
    Wrapper function to call the CLIMain class.

    Args:
    ----
        config_parser (configparser.ConfigParser): The configuration parser containing the settings.
        output_file (Optional[str]): The path to the output file.  If None, output will only be logged.

    """
    cli = CLIMain()
    cli.run(config_parser, output_file)
