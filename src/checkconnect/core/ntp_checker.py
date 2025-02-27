# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import logging
import time
from time import ctime
import ntplib


# Set up the logger at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler and set the level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

def test_ntp(ntp_file, output_file=None):
    """
    Test NTP servers for time synchronization and log the results.

    This function reads NTP server addresses from a specified file, performs
    time synchronization tests for each server, and logs the results. The
    results can either be written to an output file or printed to the console.

    Parameters
    ----------
    ntp_file (str): The path to the file containing NTP server addresses, one per line.
    output_file (str, optional): The path to the file where the output will be written.
                                 If None, the results will be printed to the console.

    Returns
    -------
    None: The function does not return a value. It either writes to the specified
          output file or prints the results to the console.

    Raises
    ------
    FileNotFoundError: If the specified NTP file does not exist, an error is logged.

    """
    logger.info("NTP-Test:")  # Ensure this line is executed
    # Open the NTP file and read the server addresses
    try:
        with open(ntp_file) as f:
            ntp_servers = [line.strip() for line in f if line.strip()]  # Strip whitespace and ignore empty lines
    except FileNotFoundError:
        logger.error("NTP file '%s' not found.", ntp_file)
        raise

    output_text = "NTP-Test:\n"  # Initialize the output text for results

    # Iterate over each NTP server and perform a time synchronization test
    for server in ntp_servers:
        try:
            client = ntplib.NTPClient()  # Create an NTP client instance
            response = client.request(server)  # Request time from the NTP server
            current_time = time.time()
            difference = response.tx_time - current_time  # Calculate the time difference
            logger.info(f"NTP: {server} - Time: {time.ctime(response.tx_time)} - difference: {difference:.2f}s")
            output_text += f"NTP: {server} - Time: {time.ctime(response.tx_time)} - difference: {difference:.2f}s\n"
        except Exception as e:
            # Log any errors encountered while querying the NTP server
            logger.error("Error retrieving time from NTP server '%s': %s", server, str(e))
            output_text += f"Issue on NTP {server}: {e}\n"

    # Check if an output file is specified
    if output_file:
        try:
            # Append the results to the specified output file
            with open(output_file, "a") as f:
                f.write(output_text)
        except Exception as e:
            logger.error("Failed to write to output file '%s': %s", output_file, str(e))
