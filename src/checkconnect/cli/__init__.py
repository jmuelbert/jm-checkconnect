# SPDX-FileCopyrightText: © 2023-2024 Jürgen Mülbert
#
# SPDX-License-Identifier: EUPL-1.2

"""__init__.py for cli.

List of names to export from cli module.

This allows __all__ to be defined in cli module, while
allowing external code to import * from cli to get just
exported names.
"""

from __future__ import annotations

import configparser
import sys
from logging import getLogger
from logging.config import fileConfig as logConfig

import click
import fpdf
import typer

from checkconnect._version import __version__

# from checkconnect.cli.application import Application
from checkconnect.core.check_ntp import test_ntp
from checkconnect.core.check_urls import test_urls

logConfig("./logging.conf", disable_existing_loggers=False)
logger = getLogger(__name__)

# app = typer.Typer()


def create_pdf() -> fpdf:
    """Creates a new PDF object.

    Creates and configures a new FPDF object, adds a blank page,
    sets the font, and returns the PDF object.

    Returns
    -------
        FPDF: The initialized PDF object.

    """
    # Create a PDF object
    pdf = fpdf()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    return pdf


@click.option(
    "-u",
    "--url-data",
    default="url.csv",
    help="the file contents the URLs to be tested",
)
@click.option(
    "-n",
    "--ntp-data",
    default="ntp.csv",
    help="the file contents the NTP servers to be tested",
)
@click.option(
    "-o",
    "--pdf_output",
    default="output.pdf",
    help="the name of the output file",
)
@click.option(
    "--config",
    "config_file",
    default="./config/settings.conf",
    help="the configuration file to use",
)
@click.version_option(version=__version__, prog_name="CheckConnect")
@click.command()
# @click.pass_context
def checkconnect(ntp_data: str, url_data: str, pdf_output: str) -> int:
    r"""cli, generate separate files from datafile.

    Args:
    ----
        ntp_data: the file contents the URLs to be tested
        url_data: the file contents the NTP servers to be tested
        pdf_output: the path and the name of the output file

    Returns:
    -------
        Status as int (0 is good)

    """

    # app = Application()

    config = configparser.ConfigParser()

    config["Path"] = {
        "url_file_name": "url.csv",
        "ntp_file_name": "ntp.csv",
        "pdf_file_name": "result.pdf",
    }

    with open("checkconnect.ini", "w", encoding="utf-8") as configfile:
        config.write(configfile)

    url_data = config.get("Path", "url_file_name", fallback="url.csv")
    ntp_data = config.get("Path", "ntp_file_name", fallback="ntp.csv")
    pdf_output = config.get("Path", "pdf_file_name", fallback="output.csv")

    pdf = create_pdf()

    # Make the tests
    test_urls(url_data, pdf)
    test_ntp(ntp_data, pdf)

    # Save PDF file
    pdf.output(pdf_output)

    # Return status
    return 0


def main() -> int:  # no cov
    """Entry point for the module."""
    checkconnect(sys.argv[1:])
    return 0


if __name__ == "__main__":
    typer.run(main)
