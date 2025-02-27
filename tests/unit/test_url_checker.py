# test_url_checker.py
# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#

import logging
import pytest
import unittest
from unittest.mock import Mock, patch
from io import StringIO
import os
import requests
import tempfile
from unittest import mock #Import mock from unittest


from checkconnect.core.url_checker import test_urls


class TestUrlChecker(unittest.TestCase):
    """Unit tests for the URL checker functionality."""
    
    def setUp(self):
            """Create a temporary test_urls.txt file and set up the logger before each test."""
            self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
            self.temp_file.write("http://example.com\n")
            self.temp_file.write("http://another-example.com\n")
            self.temp_file.write("http://nonexistent-url.com\n")
            self.temp_file.close()

            # Logger setup
            self.output_stream = StringIO()
            self.logger = logging.getLogger("CheckConnect")  # Use the same logger name as in your code
            self.logger.setLevel(logging.DEBUG)
            self.stream_handler = logging.StreamHandler(self.output_stream)
            self.logger.addHandler(self.stream_handler)
            # Add this line to ensure that the logger is not duplicated between test runs
            self.logger.propagate = False

    @patch('requests.get')
    def test_urls_success(self, mock_get):
        """Test successful URL checking."""
        mock_response_ok = Mock()
        mock_response_ok.status_code = 200
        mock_get.side_effect = [mock_response_ok, mock_response_ok, requests.exceptions.RequestException("ConnectionError")]


        output_file = "test_output.txt"

        # Capture logging output using StringIO
        with patch('checkconnect.core.url_checker.logger') as mock_logger: #Use mock_logger to replace the function's logger
            test_urls(self.temp_file.name, output_file)

            # Assertions that use the mocked logger directly.   More Robust.
            mock_logger.debug.assert_any_call(f"Checked http://example.com - Status: 200")
            mock_logger.debug.assert_any_call(f"Checked http://another-example.com - Status: 200")
            mock_logger.error.assert_called_with(f"Error on http://nonexistent-url.com: ConnectionError")
            mock_logger.info.assert_called_with(f"Results written to {output_file}")

            mock_get.assert_any_call("http://example.com", timeout=5)
            mock_get.assert_any_call("http://another-example.com", timeout=5)
            mock_get.assert_any_call("http://nonexistent-url.com", timeout=5)


        if os.path.exists(output_file):
            os.remove(output_file)

    @patch('requests.get')
    def test_urls_error(self, mock_get):
        """Test error handling during URL checking."""
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_get.return_value = mock_response_error


        output_file = "test_output.txt"
        with patch('checkconnect.core.url_checker.logger') as mock_logger:
            test_urls(self.temp_file.name, output_file)

            # Assertions that use the mocked logger directly.   More Robust.
            mock_logger.debug.assert_any_call(mock.ANY) #Any debug call will do here for a basic pass.
            mock_logger.info.assert_called_with(f"Results written to {output_file}")
            mock_get.assert_any_call("http://example.com", timeout=5)
            mock_get.assert_any_call("http://another-example.com", timeout=5)
            mock_get.assert_any_call("http://nonexistent-url.com", timeout=5)


        if os.path.exists(output_file):
            os.remove(output_file)
