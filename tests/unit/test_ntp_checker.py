# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

import pytest

from checkconnect.core.ntp_checker import NTPChecker
from tests.utils import MockLogger


class TestNTPChecker(unittest.TestCase):
    """Unit tests for NTPChecker class."""

    def setUp(self):
        """
        Set up for test methods.

        This includes:
            - Creating a config parser.
            - Initializing NTPChecker with the config parser.
            - Creating a MockLogger instance.
            - Assigning the MockLogger to the NTPChecker.
        """
        self.config_parser = configparser.ConfigParser()
        self.config_parser["Network"] = {"timeout": "10"}
        self.mock_logger = MockLogger()
        self.ntp_checker = NTPChecker(self.config_parser, logger=self.mock_logger)
        self.mock_logger.reset()

        # Translation setup
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'checkconnect', 'core', 'locales')

        try:
            self.translate = gettext.translation(
                self.TRANSLATION_DOMAIN,
                self.LOCALES_PATH,
                languages=[os.environ.get('LANG', 'en')],  # Respect the system language
            ).gettext
        except FileNotFoundError:
            # Fallback to the default English translation if the locale is not found
            def translate(message):
                return message
            self.translate = translate

    def tearDown(self):
        """Clean up after tests."""
        # If any additional cleanup is needed for your NTPChecker implementation

    def _setup_ntp_mocks(self, result_time=1678886405.0):
        """
        Helper to set up common NTP test mocks.

        Args:
            result_time: The server time to return from the mocked NTP request

        Returns:
            Tuple of mock_time, mock_ctime, mock_request
        """
        mock_time = patch("time.time", return_value=1678886400.0).start()
        mock_ctime = patch("time.ctime", return_value="Mon Mar 15 00:00:00 2023").start()
        mock_request = patch("ntplib.NTPClient.request").start()
        mock_request.return_value.tx_time = result_time

        self.addCleanup(patch.stopall)
        return mock_time, mock_ctime, mock_request

    def test_ntp_checker_initialization(self):
        """
        Test NTPChecker initializes with config.

        This test checks that the NTPChecker class is initialized correctly with the provided
        config parser and that the config_parser attribute is set as expected.
        """
        self.assertIsInstance(self.ntp_checker, NTPChecker)
        self.assertEqual(self.ntp_checker.config_parser, self.config_parser)

    @patch("checkconnect.core.ntp_checker.open", new_callable=mock_open, read_data="pool.ntp.org\n")
    def test_check_ntp_servers_success(self, mock_file):
        """
        Test successful NTP server check.

        This test mocks the open, ntplib.NTPClient.request, time.time, and time.ctime methods to simulate
        a successful NTP server check. It calls the check_ntp_servers method with a mock NTP server file
        and then checks that the expected results are returned and that the appropriate log messages are present.
        """
        mock_time, mock_ctime, mock_request = self._setup_ntp_mocks()

        results = self.ntp_checker.check_ntp_servers("ntp_servers.txt")
        expected_result = self.translate("NTP: pool.ntp.org - Time: Mon Mar 15 00:00:00 2023 - Difference: 5.00s")
        self.assertIn(expected_result, results)

        expected_info_log = self.translate("Checking NTP servers from file: ntp_servers.txt")
        self.assertIn(expected_info_log, self.mock_logger.infos)
        self.assertIn(expected_result, self.mock_logger.infos)

    def test_check_ntp_servers_with_frozen_time(self):
        """
        Test NTP server check using time mocks.
    
        Note: This test doesn't actually use freezegun due to compatibility issues.
        Instead, it manually mocks the time functions like the other tests.
        """
        # Set up the time mocks manually
        mock_time, mock_ctime, mock_request = self._setup_ntp_mocks()
        expected_result = self.translate("NTP: pool.ntp.org - Time: Mon Mar 15 00:00:00 2023 - Difference: 5.00s")

        # Create a mock for file reading
        with patch("checkconnect.core.ntp_checker.open", mock_open(read_data="pool.ntp.org\n")):
            results = self.ntp_checker.check_ntp_servers("ntp_servers.txt")

        # Check for the expected time difference in the results
        self.assertTrue(any("Difference: 5.00s" in r for r in results),
                  f"Expected to find a time difference of 5.00s in results. Got: {results}")

    @patch("checkconnect.core.ntp_checker.open", side_effect=FileNotFoundError)
    def test_check_ntp_servers_file_not_found(self, mock_file):
        """
        Test when NTP file is not found.

        This test mocks the open method to raise a FileNotFoundError to simulate the scenario where the
        specified NTP server file does not exist. It asserts that the expected error message is returned and logged.
        """
        results = self.ntp_checker.check_ntp_servers("nonexistent_file.txt")
        expected_error = self.translate("Error: NTP file not found: nonexistent_file.txt")
        self.assertIn(expected_error, results)

        translated_error = self.translate("NTP file not found: nonexistent_file.txt")
        self.assertIn(translated_error, self.mock_logger.errors)

    @patch("checkconnect.core.ntp_checker.open", side_effect=Exception("Read error"))
    def test_check_ntp_servers_file_read_error(self, mock_file):
        """
        Test when there is an error reading the NTP file.

        This test mocks the open method to raise a generic Exception to simulate an error occurring while
        attempting to read the NTP server file. It asserts that the expected error message is returned and logged.
        """
        results = self.ntp_checker.check_ntp_servers("ntp_servers.txt")
        expected_result = self.translate("Error: Could not read NTP file: Read error")
        self.assertIn(expected_result, results)

        expected_exception = self.translate("Error reading NTP file: Read error")
        self.assertIn(expected_exception, "".join(self.mock_logger.exceptions))

    @patch("checkconnect.core.ntp_checker.open", new_callable=mock_open, read_data="pool.ntp.org\n")
    @patch("ntplib.NTPClient.request", side_effect=Exception("NTP request failed"))
    def test_check_ntp_servers_request_error(self, mock_request, mock_file):
        """
        Test when there is an error during the NTP request.

        This test mocks the open and ntplib.NTPClient.request methods to simulate an error occurring
        during the NTP request process. It asserts that the expected error message is returned and logged.
        """
        results = self.ntp_checker.check_ntp_servers("ntp_servers.txt")
        expected_error = self.translate("Error retrieving time from NTP server pool.ntp.org: NTP request failed")
        self.assertIn(expected_error, results)
        self.assertIn(expected_error, self.mock_logger.errors)

    def test_check_ntp_servers_write_output_file(self):
        """
        Test successful NTP server check and writing to output file.

        This test mocks the open (for both reading and writing), ntplib.NTPClient.request, time.time,
        and time.ctime methods to simulate a successful NTP server check and the writing of results to an
        output file. It calls the check_ntp_servers method with both an NTP server file and an output file,
        and then checks that the expected results are returned, that the results are written to the output file,
        and that the appropriate log messages are present.
        """
        mock_time, mock_ctime, mock_request = self._setup_ntp_mocks()
        expected_result = self.translate("NTP: pool.ntp.org - Time: Mon Mar 15 00:00:00 2023 - Difference: 5.00s")

        # Create a mock for both reading and writing
        mocked_open = mock_open(read_data="pool.ntp.org\n")

        with patch("checkconnect.core.ntp_checker.open", mocked_open):
            results = self.ntp_checker.check_ntp_servers("ntp_servers.txt", "output.txt")

        self.assertIn(expected_result, results)

        # Check that the file was written to with the expected content
        write_calls = mocked_open().write.call_args_list

        # Make sure the write method was called
        self.assertTrue(len(write_calls) > 0, "write() was not called")

        # Convert calls to strings for easier assertion
        write_data = ''.join(call_args[0][0] for call_args in write_calls)
        self.assertIn(expected_result, write_data)

        # Alternatively, you can check if any specific call had the exact content
        expected_call_found = False
        for call_args in write_calls:
            if call_args[0][0] == f"{expected_result}\n":
                expected_call_found = True
                break

        self.assertTrue(expected_call_found, f"No write call with exactly '{expected_result}\\n' was found")

        # Check log messages
        self.assertIn(self.translate("Results written to output.txt"), self.mock_logger.infos)

    def test_check_ntp_servers_write_output_file_error(self):
        """
        Test when there is an error writing to the output file.

        This test uses a simpler approach by mocking the file reading normally but then
        patching a separate method for writing results.
        """
        mock_time, mock_ctime, mock_request = self._setup_ntp_mocks()
        expected_result = self.translate("NTP: pool.ntp.org - Time: Mon Mar 15 00:00:00 2023 - Difference: 5.00s")

        # Simplified approach: mock reading separately from writing
        with patch("checkconnect.core.ntp_checker.open", mock_open(read_data="pool.ntp.org\n")):
            # For writing, we'll simulate a failure when attempting to open the output file
            # by patching 'open' with a side_effect for the output file only

            # Define a custom side effect for open that raises an exception for output.txt
            original_open = open
            def custom_open_side_effect(*args, **kwargs):
                if args and args[0] == "output.txt":
                    raise Exception("Write error")
                return mock_open(read_data="pool.ntp.org\n")(*args, **kwargs)

            with patch("checkconnect.core.ntp_checker.open", side_effect=custom_open_side_effect):
                results = self.ntp_checker.check_ntp_servers("ntp_servers.txt", "output.txt")

        self.assertIn(expected_result, results)
        self.assertIn(self.translate("Error writing to output file: Write error"), self.mock_logger.errors)

    @patch("checkconnect.core.ntp_checker.open", new_callable=mock_open, read_data="pool.ntp.org\ntime.nist.gov\n")
    def test_check_ntp_servers_multiple_servers(self, mock_file):
        """Test checking multiple NTP servers."""
        mock_time, mock_ctime, mock_request = self._setup_ntp_mocks()

        results = self.ntp_checker.check_ntp_servers("ntp_servers.txt")

        # Check that we got results for both servers
        self.assertEqual(len(results), 2, "Should get results for two servers")
        self.assertTrue(any("pool.ntp.org" in r for r in results), "Expected pool.ntp.org in results")
        self.assertTrue(any("time.nist.gov" in r for r in results), "Expected time.nist.gov in results")

    @patch("checkconnect.core.ntp_checker.open", new_callable=mock_open, read_data="")
    def test_check_ntp_servers_empty_file(self, mock_file):
        """Test checking an empty NTP server file."""
        results = self.ntp_checker.check_ntp_servers("ntp_servers.txt")

        # Check that we got no results
        self.assertEqual(len(results), 0, "Should get no results for empty file")

        # Check that appropriate warning was logged
        # Note: You may need to update this based on your actual implementation
        # self.assertIn("No NTP servers found in file", self.mock_logger.warnings)

    def test_ntp_checker_cleanup(self):
        """
        Test that NTPChecker properly cleans up resources when done.

        This is a placeholder test - implement with actual cleanup checks
        based on your NTPChecker implementation.
        """
        # Example: If NTPChecker has a close() method to clean up resources
        # self.ntp_checker.close()
        # self.assertFalse(hasattr(self.ntp_checker, "_open_resources"))
