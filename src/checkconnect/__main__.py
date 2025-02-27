# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2023-present Jürgen Mülbert
#

"""Main entry point for CheckConnect."""

import logging
import sys

import click

from checkconnect.cli.main import cli_main
from checkconnect.gui.main import gui_main


@click.command()
@click.option("--gui", is_flag=True, help="Start the GUI version")
@click.option("-c", "--config", type=click.Path(exists=True), help="Path to the configuration file")
@click.option("-o", "--output", type=click.Path(), help="Path to the output file")
@click.option("-v", "--verbose", is_flag=True, help="Enable detailed logs")
def main(gui, config, output, verbose):
    """
    Main function for CheckConnect.

    This function sets up logging and decides whether to run
    the CLI or GUI version of CheckConnect based on user input.

    Parameters
    ----------
    gui : bool
        If set, launches the GUI version instead of the CLI.
    config : str or None
        Path to the configuration file, if provided.
    output : str or None
        Path to the output file, if specified.
    verbose : bool
        If set, enables detailed debug logs.

    """
    # Configure logging based on verbosity flag
    logging_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s")

    logging.info("Starting CheckConnect")

    # Determine execution mode
    if gui:
        logging.info("Launching GUI mode")
        gui_main(config, output)
    else:
        logging.info("Launching CLI mode")
        cli_main(config, output)

# Run the main function when the script is executed directly
if __name__ == "__main__":
    main()
