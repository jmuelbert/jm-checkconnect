# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Main entry point for the CLI.

This script initializes the CLI mode for the CheckConnect application.
It performs connectivity tests for NTP servers and URLs and generates reports.
"""

import logging

from checkconnect.core.create_reports import create_html_report, create_pdf_report
from checkconnect.core.ntp_checker import test_ntp
from checkconnect.core.url_checker import test_urls

from checkconnect.cli.checkconnect import CheckConnect

def cli_main(config_file, output_file):
    """
    Main function for the CLI.

    This function:
    - Configures logging.
    - Runs NTP and URL connectivity tests.
    - Generates reports in PDF and HTML format.

    Args:
    ----
        config_file (str): Path to the configuration file (currently unused).
        output_file (str): Path to the output log file.

    """
    logger = logging.getLogger("CheckConnect")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Running CheckConnect in CLI mode")

    check_connect = CheckConnect(config_file, output_file)
    check_connect.run()
    check_connect.generate_reports()

    logger.info("Reports have been generated.")
