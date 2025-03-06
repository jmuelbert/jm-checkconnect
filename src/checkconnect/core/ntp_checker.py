# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
import time
from typing import List

import ntplib

# Define the translation domain
TRANSLATION_DOMAIN = "checkconnect"

# Set the locales path relative to the current file
LOCALES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "core",
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


class NTPChecker:
    """
    Checks the time synchronization with NTP servers.
    """

    def __init__(
        self,
        config_parser: configparser.ConfigParser,
        logger: logging.Logger = None,
    ):
        """
        Initializes the NTPChecker with a configuration parser.

        Args:
        ----
            config_parser (configparser.ConfigParser): The configuration parser containing the settings.
            logger (logging.Logger, optional): A logger instance. If None, a default logger is created.

        """
        self.config_parser = config_parser
        self.logger = logger or logging.getLogger(
            __name__,
        )  # Create a logger instance if none is passed in

    def check_ntp_servers(self, ntp_file: str, output_file: str = None) -> list[str]:
        """
        Checks time synchronization with NTP servers in a file.

        Args:
        ----
            ntp_file (str): The path to the file containing the NTP servers.
            output_file (str, optional): The path to the file to write the results to. Defaults to None.

        Returns:
        -------
            List[str]: A list of strings, each representing the result of checking an NTP server.  If errors occur during file reading, a list containing a single error string is returned.

        """
        self.logger.info(translate(f"Checking NTP servers from file: {ntp_file}"))
        try:
            with open(ntp_file) as f:
                ntp_servers = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            error_message = translate(f"NTP file not found: {ntp_file}")
            self.logger.error(error_message)
            return [
                f"Error: NTP file not found: {ntp_file}",
            ]  # Keep the Error: prefix for now, in case tests rely on this
        except Exception as e:
            error_message = translate(f"Error reading NTP file: {e}")
            self.logger.exception(error_message)
            return [
                f"Error: Could not read NTP file: {e}",
            ]  # Keep the Error: prefix for now, in case tests rely on this

        results = []
        for server in ntp_servers:
            try:
                client = ntplib.NTPClient()
                response = client.request(server, version=3)
                current_time = time.time()
                difference = response.tx_time - current_time
                result = translate(
                    f"NTP: {server} - Time: {time.ctime(response.tx_time)} - Difference: {difference:.2f}s",
                )
                self.logger.info(result)
                results.append(result)  # Add result to the list
            except Exception as e:
                error_message = translate(
                    f"Error retrieving time from NTP server {server}: {e}",
                )
                self.logger.error(error_message)
                results.append(error_message)

        # Write results to output file if specified
        if output_file:
            try:
                with open(output_file, "a") as f:
                    for result in results:
                        f.write(result + "\n")
                self.logger.info(translate(f"Results written to {output_file}"))
            except Exception as e:
                self.logger.error(translate(f"Error writing to output file: {e}"))

        return results  # returning a list of results
