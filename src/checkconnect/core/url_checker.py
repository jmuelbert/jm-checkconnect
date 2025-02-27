# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import logging
import requests

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

def test_urls(url_file, output_file):
    """
    Test a list of URLs for HTTP status and log the results.

    This function reads URLs from a specified file, performs HTTP GET requests
    for each URL, and logs the results. The results can either be written to
    an output file or printed to the console.

    Parameters
    ----------
    url_file (str): The path to the file containing URLs, one per line.
    output_file (str): The path to the file where the output will be written. If None,
                       the results will be printed to the console.

    Returns
    -------
    None: The function does not return a value. It either writes to the specified
          output file or prints the results to the console.

    Raises
    ------
    FileNotFoundError: If the specified URL file does not exist, an error is logged.

    """

    try:
        # Open the URL file and read the URLs
        with open(url_file) as f:
            # Strip whitespace and ignore empty lines
            urls = [line.strip() for line in f if line.strip()]

        output_text = "URL-Test:\n"  # Initialize the output text for results

        # Iterate over each URL and perform an HTTP GET request
        for url in urls:
            try:
                # Send a GET request to the URL with a timeout of 5 seconds
                response = requests.get(url, timeout=5)
                # Append the URL and its HTTP status code to the output text
                output_text += f"URL: {url} - Status: {response.status_code}\n"
                logger.debug(f"Checked {url} - Status: {response.status_code}")
            except requests.RequestException as e:
                # Log any errors encountered while querying the URL
                output_text += f"Issue on URL {url}: {e}\n"
                logger.error(f"Error on {url}: {e}")

        # Check if an output file is specified
        if output_file:
            # Append the results to the specified output file
            try:
                with open(output_file, "a") as f:
                    f.write(output_text)
                logger.info(f"Results written to {output_file}")
            except IOError as e:
                logger.error(f"Error writing to output file: {e}")
        else:
            # Print the results to the console if no output file is specified
            print(output_text)

    except FileNotFoundError:
        # Log an error if the URL file is not found
        logger.error(f"URL file {url_file} not found")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
