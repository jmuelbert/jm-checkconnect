# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import gettext
import logging
import os
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

from checkconnect.core.create_reports import HTML, ReportGenerator
from tests.utils import MockLogger


class TestReportGenerator(unittest.TestCase):
    """Unit tests for the ReportGenerator class in checkconnect/core/create_reports.py."""

    def setUp(self):
        """
        Set up for test methods.

        This includes:
            - Creating a MockLogger instance.
            - Creating a temporary directory.
            - Initializing ReportGenerator with mock file names and the temporary directory.
            - Assigning the MockLogger to the ReportGenerator.
            - Resetting the MockLogger.
        """
        self.mock_logger = MockLogger()
        self.temp_dir = tempfile.TemporaryDirectory()  # Create a temporary directory
        self.report_generator = ReportGenerator(
            "ntp_file.txt",
            "url_file.txt",
            self.temp_dir.name,
            logger=self.mock_logger,
        )
        self.mock_logger.reset()

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

    def tearDown(self):
        """
        Clean up the temporary directory after tests.

        This ensures that the temporary directory and its contents are removed after each test,
        preventing interference between tests and cleaning up resources.
        """
        self.temp_dir.cleanup()

    @patch(
        "checkconnect.core.create_reports.ReportGenerator._read_file",
        return_value="ntp data",
    )
    @patch("os.makedirs", return_value=None)
    def test_create_html_report_success(self, mock_makedirs, mock_read_file):
        """
        Test successful creation of HTML report.

        This test mocks the ReportGenerator._read_file, os.makedirs methods to simulate
        a successful HTML report creation. It calls the create_html_report method and then
        checks that the necessary methods are called and that the expected log messages are present.
        """
        self.report_generator.create_html_report()

        # Check Log Messages
        logged_messages = self.mock_logger.infos
        self.assertEqual(len(logged_messages), 1)  # Expect one info message
        expected_message = self.translate(
            f"HTML report generated at {os.path.join(self.temp_dir.name, 'report.html')}",
        )
        self.assertEqual(logged_messages[0], expected_message)

    @patch(
        "checkconnect.core.create_reports.ReportGenerator._read_file",
        side_effect=FileNotFoundError("File not found"),
    )
    def test_create_html_report_file_not_found(self, mock_read_file):
        """
        Test HTML report creation when a file is not found.

        This test mocks the ReportGenerator._read_file method to raise a FileNotFoundError to simulate a file
        not found error during HTML report creation. It asserts that the expected exception is raised.
        """
        with self.assertRaisesRegex(FileNotFoundError, "File not found"):
            self.report_generator.create_html_report()

    @patch(
        "checkconnect.core.create_reports.ReportGenerator._read_file",
        side_effect=Exception("Generic error"),
    )
    def test_create_html_report_generic_error(self, mock_read_file):
        """
        Test HTML report creation when a generic error occurs.

        This test mocks the ReportGenerator._read_file method to raise a generic Exception to simulate an error
        during HTML report creation. It asserts that the expected exception is raised.
        """
        with self.assertRaisesRegex(Exception, "Generic error"):
            self.report_generator.create_html_report()

    @patch(
        "checkconnect.core.create_reports.ReportGenerator._read_file",
        return_value="ntp data",
    )
    @patch(
        "pathlib.Path.mkdir",
        return_value=None,
    )  # Changed from os.makedirs to Path.mkdir
    @patch("checkconnect.core.create_reports.HTML")
    def test_create_pdf_report_success(self, mock_html, mock_mkdir, mock_read_file):
        """
        Test successful creation of PDF report.

        This test mocks the ReportGenerator._read_file, Path.mkdir, and HTML methods to simulate
        a successful PDF report creation using WeasyPrint. It calls the create_pdf_report method and then
        checks that the necessary methods are called with the correct arguments.
        """
        # Set up the mock correctly to return an object with write_pdf method
        mock_write_pdf = MagicMock()

        # Add attributes needed for the debug log call
        mock_html.__name__ = "MockHTML"
        mock_html.__module__ = "mock_module"

        # Configure the return value with the write_pdf method
        mock_html.return_value = MagicMock(write_pdf=mock_write_pdf)

        # Call the method to generate the PDF report
        self.report_generator.create_pdf_report()

        # Ensure the necessary methods were called - note we changed the assertion
        # to check Path.mkdir instead of os.makedirs
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Ensure that HTML was called with the right arguments
        mock_html.assert_called_once()

        # Get the actual arguments passed to HTML
        args, kwargs = mock_html.call_args

        # Verify the string argument
        self.assertIn("<html", kwargs.get("string", ""))

        # Ensure that write_pdf was called with the correct output path
        # We need to convert to string because Path objects are passed to str() in the code
        expected_path = str(self.report_generator.output_dir / "report.pdf")
        mock_write_pdf.assert_called_once_with(expected_path)

        # Check Log Messages
        logged_messages = self.mock_logger.infos
        self.assertEqual(len(logged_messages), 2)  # Expect two info messages

        # Adjust the expected messages to match the new implementation
        self.assertIn(
            "Creating PDF report",
            logged_messages[0],
        )  # Check part of the message
        self.assertIn(
            "PDF report generated at",
            logged_messages[1],
        )  # Check part of the message

    @patch(
        "checkconnect.core.create_reports.ReportGenerator._read_file",
        side_effect=FileNotFoundError("File not found"),
    )
    def test_create_pdf_report_file_not_found(self, mock_read_file):
        """
        Test PDF report creation when a file is not found.

        This test mocks the ReportGenerator._read_file method to raise a FileNotFoundError to simulate a file
        not found error during PDF report creation. It asserts that the expected exception is raised.
        """
        with self.assertRaisesRegex(FileNotFoundError, "File not found"):
            self.report_generator.create_pdf_report()

    @patch(
        "checkconnect.core.create_reports.ReportGenerator._read_file",
        return_value="ntp data",
    )
    @patch("os.makedirs", return_value=None)
    @patch("checkconnect.core.create_reports.HTML")
    def test_create_pdf_report_generic_error(
        self,
        mock_html,
        mock_makedirs,
        mock_read_file,
    ):
        """
        Test PDF report creation when a generic error occurs.

        This test mocks the ReportGenerator._read_file, os.makedirs and HTML methods to simulate
        an error during PDF report creation, specifically within the WeasyPrint library. It asserts that the
        expected exception is raised and that the exception message matches the WeasyPrint error message.
        """
        # Add name attributes to avoid attribute errors
        mock_html.__name__ = "MockHTML"
        mock_html.__module__ = "mock_module"

        # Configure the mock to raise an exception when called
        mock_html.side_effect = Exception("WeasyPrint error")

        with self.assertRaises(Exception) as context:
            self.report_generator.create_pdf_report()

        # Ensure the exception message is what we expect
        self.assertEqual(str(context.exception), "WeasyPrint error")
