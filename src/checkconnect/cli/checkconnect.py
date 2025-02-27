# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
CheckConnect: A tool for checking network connectivity.

This module provides a `CheckConnect` class that performs network connectivity
tests for NTP servers and URLs. It also generates reports in PDF and HTML format.
"""
import logging

from checkconnect.core.create_reports import create_html_report, create_pdf_report
from checkconnect.core.ntp_checker import test_ntp
from checkconnect.core.url_checker import test_urls


class CheckConnect:
    """
    Handles network connectivity checks and report generation.

    This class:
    - Initializes logging.
    - Runs network tests for NTP servers and URLs.
    - Generates reports based on the test results.

    Attributes
    ----------
        config_file (str | None): Optional path to a configuration file.
        output_file (str | None): Path to the output file where results are stored.
        logger (logging.Logger): Logger instance for logging messages.

    """

    def __init__(self, config_file: str = None, output_file: str = None):
        """
        Initializes the CheckConnect instance.

        Args:
        ----
            config_file (str, optional): Path to a configuration file. Defaults to None.
            output_file (str, optional): Path to an output file. Defaults to None.

        """
        self.config_file = config_file
        self.output_file = output_file
        self.logger = logging.getLogger("CheckConnect")
        self.setup_logging()

    def setup_logging(self):
        """Configures logging settings for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def run(self):
        """
        Runs network connectivity checks.

        This method tests connectivity to NTP servers and URLs.
        If an error occurs during execution, it is logged.
        """
        self.logger.info("Starting CheckConnect...")

        # Define input files for NTP and URL tests
        ntp_file = "ntp_servers.csv"
        url_file = "urls.csv"

        try:
            # Run connectivity tests
            test_ntp(ntp_file, self.output_file)
            test_urls(url_file, self.output_file)
            self.logger.info("Tests completed successfully.")
        except Exception as e:
            # Log any errors that occur during testing
            self.logger.error(f"Error during tests: {e}", exc_info=True)

    def generate_reports(self):
        """
        Generates reports based on test results.

        Creates both PDF and HTML reports using the results from
        the NTP and URL tests. Errors during report generation are logged.
        """
        try:
            create_pdf_report("ntp_servers.csv", "urls.csv")
            create_html_report("ntp_servers.csv", "urls.csv")
            self.logger.info("Reports generated successfully.")
        except Exception as e:
            # Log any errors that occur while generating reports
            self.logger.error(f"Error while generating reports: {e}", exc_info=True)


if __name__ == "__main__":
    # Create an instance of CheckConnect with an optional output file
    CheckConnect().run()
