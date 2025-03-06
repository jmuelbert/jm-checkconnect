# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

import requests

from checkconnect.core.url_checker import URLChecker
from tests.utils import MockLogger


class TestURLChecker(unittest.TestCase):
    """Unit tests for URLChecker class."""

    def setUp(self):
        """
        Set up for test methods.

        This includes:
            - Creating a config parser.
            - Initializing URLChecker with the config parser.
            - Creating a MockLogger instance.
            - Assigning the MockLogger to the URLChecker.
        """
        self.config_parser = configparser.ConfigParser()
        self.config_parser["Network"] = {"timeout": "10"}
        self.mock_logger = MockLogger()
        self.url_checker = URLChecker(
            self.config_parser,
            logger=self.mock_logger,
        )  # set logger
        # self.url_checker.logger = self.mock_logger # NO set direct the instance!

        # Translation setup
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "checkconnect",
            "core",
            "locales",
        )

        try:
            self.translate = gettext.translation(
                self.TRANSLATION_DOMAIN,
                self.LOCALES_PATH,
                languages=[os.environ.get("LANG", "en")],  # Respect the system language
            ).gettext
        except FileNotFoundError:
            # Fallback to the default English translation if the locale is not found
            def translate(message):
                return message

            self.translate = translate

    def test_url_checker_initialization(self):
        """
        Test URLChecker initializes with config.

        This test verifies that the URLChecker class is initialized correctly with the provided
        config parser and that the timeout value is extracted from the config and assigned to the
        corresponding attribute.
        """
        self.assertEqual(self.url_checker.config_parser, self.config_parser)
        self.assertEqual(self.url_checker.timeout, 10)  # Verify timeout from config

    @patch(
        "checkconnect.core.url_checker.open",
        new_callable=mock_open,
        read_data="https://www.example.com\n",
    )
    @patch("requests.get")
    def test_check_urls_success(self, mock_get, mock_file):
        """
        Test successful URL check.

        This test mocks the open and requests.get methods to simulate a successful URL check. It calls
        the check_urls method with a mock URL file and then checks that the expected results are returned
        and that the appropriate log messages are present.
        """
        self.mock_logger.reset()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        results = self.url_checker.check_urls("urls.txt")  # run
        expected_result = self.translate("URL: https://www.example.com - Status: 200")
        self.assertIn(expected_result, results)

        expected_log = self.translate("Checking URLs from file: urls.txt")
        self.assertIn(expected_log, self.mock_logger.infos)
        self.assertIn(expected_result, self.mock_logger.infos)

    @patch("checkconnect.core.url_checker.open", side_effect=FileNotFoundError)
    def test_check_urls_file_not_found(self, mock_file):
        """
        Test when URL file is not found.

        This test mocks the open method to raise a FileNotFoundError to simulate the scenario where the
        specified URL file does not exist. It asserts that the expected error message is returned and logged.
        """
        self.mock_logger.reset()

        results = self.url_checker.check_urls("nonexistent_file.txt")
        expected_result = self.translate(
            "Error: URL file not found: nonexistent_file.txt",
        )
        self.assertIn(expected_result, results)

        error_log = self.translate("URL file not found: nonexistent_file.txt")
        self.assertIn(error_log, self.mock_logger.errors)

    @patch("checkconnect.core.url_checker.open", side_effect=Exception("Read error"))
    def test_check_urls_file_read_error(self, mock_file):
        """
        Test when there is an error reading the URL file.

        This test mocks the open method to raise a generic Exception to simulate an error occurring while
        attempting to read the URL file. It asserts that the expected error message is returned and logged.
        """
        self.mock_logger.reset()

        results = self.url_checker.check_urls("urls.txt")
        expected_result = self.translate("Error: Could not read URL file: Read error")
        self.assertIn(expected_result, results)

        exception_log = self.translate("Error reading URL file: Read error")
        self.assertIn(exception_log, "".join(self.mock_logger.exceptions))

    @patch(
        "checkconnect.core.url_checker.open",
        new_callable=mock_open,
        read_data="https://www.example.com\n",
    )
    @patch("requests.get", side_effect=requests.RequestException("Connection error"))
    def test_check_urls_request_error(self, mock_get, mock_file):
        """
        Test when there is a request exception.

        This test mocks the open and requests.get methods to simulate an error occurring during the
        HTTP request. It asserts that the expected error message is returned and logged.
        """
        self.mock_logger.reset()

        results = self.url_checker.check_urls("urls.txt")
        expected_result = self.translate(
            "Error checking URL https://www.example.com: Connection error",
        )
        self.assertIn(expected_result, results)

        self.assertIn(expected_result, self.mock_logger.errors)

    @patch(
        "checkconnect.core.url_checker.open",
        new_callable=mock_open,
        read_data="https://www.example.com\n",
    )
    @patch("requests.get")
    def test_check_urls_write_output_file(self, mock_get, mock_open):
        """
        Test successful URL check and writing to output file.

        This test mocks the open and requests.get methods to simulate a successful URL check and the
        writing of the results to an output file. It calls the check_urls method with both a URL file
        and an output file, and then checks that the expected results are returned, that the results are
        written to the output file, and that the appropriate log messages are present.
        """
        self.mock_logger.reset()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        mock_open_instance = mock_open.return_value
        mock_write = MagicMock()
        mock_open_instance.write = mock_write
        expected_result = self.translate("URL: https://www.example.com - Status: 200")

        results = self.url_checker.check_urls("urls.txt", "output.txt")

        self.assertIn(expected_result, results)
        mock_write.assert_called_once_with(f"{expected_result}\n")
        self.assertIn(
            self.translate("Results written to output.txt"),
            self.mock_logger.infos,
        )

    @patch(
        "checkconnect.core.url_checker.open",
        new_callable=mock_open,
        read_data="https://www.example.com\n",
    )
    @patch("requests.get")
    def test_check_urls_write_output_file_error(self, mock_get, mock_open):
        """
        Test handling a write error.

        This test mocks the open and requests.get methods to simulate a successful URL check but an error
        occurring while attempting to write the results to the output file. It asserts that the expected
        results are returned and that the write error is logged.
        """
        self.mock_logger.reset()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        mock_open_instance = mock_open.return_value
        mock_write = MagicMock(side_effect=Exception("Write error"))
        mock_open_instance.write = mock_write
        expected_result = self.translate("URL: https://www.example.com - Status: 200")

        results = self.url_checker.check_urls("urls.txt", "output.txt")

        self.assertIn(expected_result, results)
        self.assertIn(
            self.translate("Error writing to output file: Write error"),
            self.mock_logger.errors,
        )
