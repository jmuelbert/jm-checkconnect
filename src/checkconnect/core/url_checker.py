# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
from typing import List

import requests

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


class URLChecker:
    """
    Checks the HTTP status of URLs.
    """

    def __init__(
        self,
        config_parser: configparser.ConfigParser,
        logger: logging.Logger = None,
    ):
        """
        Initializes the URLChecker with a configuration parser.

        Args:
        ----
            config_parser (configparser.ConfigParser): The configuration parser containing the settings.
            logger (logging.Logger, optional): A logger instance. If None, a default logger is created.

        """
        self.config_parser = config_parser
        self.timeout = self.config_parser.getint(
            "Network",
            "timeout",
            fallback=5,
        )  # Timeout read from Config
        self.logger = logger or logging.getLogger(
            __name__,
        )  # Create a logger instance if none is passed in

    def check_urls(self, url_file: str, output_file: str = None) -> list[str]:
        """
        Checks the HTTP status of URLs in a file.

        Args:
        ----
            url_file (str): The path to the file containing the URLs.
            output_file (str, optional): The path to the file to write the results to. Defaults to None.

        Returns:
        -------
            List[str]: A list of strings, each representing the result of checking a URL.  If errors occur during file reading, a list containing a single error string is returned.

        """
        self.logger.info(translate(f"Checking URLs from file: {url_file}"))
        try:
            with open(url_file) as f:
                urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            error_message = translate(f"URL file not found: {url_file}")
            self.logger.error(error_message)
            return [
                f"Error: URL file not found: {url_file}",
            ]  # Keep the Error: prefix for now, in case tests rely on this
        except Exception as e:
            error_message = translate(f"Error reading URL file: {e}")
            self.logger.exception(error_message)
            return [
                f"Error: Could not read URL file: {e}",
            ]  # Keep the Error: prefix for now, in case tests rely on this

        if not urls:
            self.logger.warning(translate("No URLs found in the file."))
            return [translate("No URLs found in the file.")]

        results = []
        for url in urls:
            try:
                response = requests.get(url, timeout=self.timeout)
                result = translate(f"URL: {url} - Status: {response.status_code}")
                self.logger.info(result)
                results.append(result)
            except requests.RequestException as e:
                error_message = translate(f"Error checking URL {url}: {e}")
                self.logger.error(error_message)
                results.append(error_message)

        if output_file:
            try:
                with open(output_file, "w") as f:  # Change to "w" to overwrite
                    for result in results:
                        f.write(result + "\n")
                self.logger.info(translate(f"Results written to {output_file}"))
            except Exception as e:
                self.logger.error(translate(f"Error writing to output file: {e}"))

        return results  # returning a list of results
