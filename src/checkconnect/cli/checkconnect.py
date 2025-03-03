# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
from typing import Optional

# Add these import statements
from checkconnect.core.create_reports import (
    ReportGenerator,
    create_html_report,
    create_pdf_report,
)
from checkconnect.core.ntp_checker import NTPChecker
from checkconnect.core.url_checker import URLChecker

# Define the translation domain
TRANSLATION_DOMAIN = "checkconnect"

# Set the locales path relative to the current file
LOCALES_PATH = os.path.join(os.path.dirname(__file__), 'locales')

# Initialize gettext
try:
    translate = gettext.translation(
        TRANSLATION_DOMAIN,
        LOCALES_PATH,
        languages=[os.environ.get('LANG', 'en')],  # Respect the system language
    ).gettext
except FileNotFoundError:
    # Fallback to the default English translation if the locale is not found
    def translate(message):
        return message


class CheckConnect:
    """
    Handles network connectivity checks and report generation.
    """

    def __init__(self, config_parser: configparser.ConfigParser, output_file: Optional[str] = None):
        """
        Initializes the CheckConnect instance.

        Args:
        ----
            config_parser (configparser.ConfigParser): The configuration parser containing the settings.
            output_file (Optional[str], optional): The path to the output file. Defaults to None.

        """
        self.config_parser = config_parser
        self.output_file = output_file
        self.ntp_file = self.config_parser.get("Files", "ntp_servers", fallback="ntp_servers.csv")
        self.url_file = self.config_parser.get("Files", "urls", fallback="urls.csv")
        self.url_checker = URLChecker(config_parser)
        self.ntp_checker = NTPChecker(config_parser)
        self.report_dir = self.config_parser.get("Output", "directory", fallback="reports")  # from the ConfigFile
        self.logger = logging.getLogger(__name__)  # Get logger for this module

    def run(self, ntp_file: Optional[str] = None, url_file: Optional[str] = None) -> None:
        """
        Runs network connectivity checks.

        Args:
        ----
            ntp_file (Optional[str], optional): The path to the NTP server file. Defaults to None.
            url_file (Optional[str], optional): The path to the URL file. Defaults to None.

        Raises:
        ------
            FileNotFoundError: Raised if one of the specified files is not found.
            Exception: Raised if an error occurs during the tests.

        """
        self.logger.info(translate("Starting CheckConnect..."))

        # Use default files from config if no arguments are provided
        ntp_file = ntp_file or self.ntp_file
        url_file = url_file or self.url_file

        try:
            # Run connectivity tests
            self.ntp_checker.check_ntp_servers(ntp_file, self.output_file)
            self.url_checker.check_urls(url_file, self.output_file)
            self.logger.info(translate("Tests completed successfully."))
        except FileNotFoundError as e:
            self.logger.error(translate(f"File not found: {e}"))
            raise
        except Exception as e:
            self.logger.exception(translate(f"Error during tests: {e}"))
            raise  # Re-raise to propagate the error

    def generate_reports(self, ntp_file: Optional[str] = None, url_file: Optional[str] = None) -> None:
        """
        Generates reports based on the NTP and URL test results.

        Args:
        ----
            ntp_file (Optional[str], optional): The path to the NTP server file. Defaults to None.
            url_file (Optional[str], optional): The path to the URL file. Defaults to None.

        Raises:
        ------
            Exception: Raised if an error occurs during report generation.

        """
        self.logger.info(translate("Starting report generation..."))

        ntp_file = ntp_file or self.ntp_file
        url_file = url_file or self.url_file

        try:
            create_pdf_report(ntp_file, url_file, self.report_dir)
            create_html_report(ntp_file, url_file, self.report_dir)
            self.logger.info(translate("Reports generated successfully."))
        except Exception as e:
            self.logger.exception(translate(f"Error while generating reports: {e}"))
