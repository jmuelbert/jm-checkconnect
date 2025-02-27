# test_ntp_checker.py
# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#

import logging
import unittest
from unittest.mock import patch
from io import StringIO
import tempfile
import ntplib
from checkconnect.core.ntp_checker import test_ntp

class TestNtpChecker(unittest.TestCase):
    """Unit tests for the NTP checker functionality."""

    def setUp(self):
        """Create a temporary NTP file and set up the logger before each test."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
        self.temp_file.write("europe.pool.ntp.org\n")
        self.temp_file.write("time.google.com\n")
        self.temp_file.close()

        # Logger setup
        self.output_stream = StringIO()
        self.logger = logging.getLogger("CheckConnect")  # Use the same logger name as in your code
        self.logger.setLevel(logging.DEBUG)
        self.stream_handler = logging.StreamHandler(self.output_stream)
        self.logger.addHandler(self.stream_handler)
        # Prevent logger from propagating to the root logger
        self.logger.propagate = False

    @patch("checkconnect.core.ntp_checker.ntplib.NTPClient.request")
    @patch("checkconnect.core.ntp_checker.logger")  # Mock the logger
    def test_ntp_error(self, mock_logger, mock_request):
        """
        Test the error handling when the NTP server is unreachable.

        This test mocks the NTPClient.request method to raise an exception,
        simulating a scenario where the NTP server cannot be reached. It
        verifies that the appropriate error messages are printed for each server.
        """
        # Simulate a connection error by raising an exception
        mock_request.side_effect = ntplib.NTPException("Connection error")

        with patch("builtins.print"):
            test_ntp(self.temp_file.name, None)

            # Assert that the logger was called with the expected messages
            mock_logger.info.assert_any_call("NTP-Test:")
            mock_logger.error.assert_any_call("Error retrieving time from NTP server '%s': %s", 'europe.pool.ntp.org', 'Connection error')
            mock_logger.error.assert_any_call("Error retrieving time from NTP server '%s': %s", 'time.google.com', 'Connection error')

    def tearDown(self):
        """Remove the temporary file after each test."""
        import os
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

if __name__ == "__main__":
    unittest.main()
