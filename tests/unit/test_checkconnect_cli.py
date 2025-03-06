# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import os
import unittest
from unittest.mock import MagicMock, patch

from checkconnect.cli.checkconnect import CheckConnect
from tests.utils import MockLogger


class TestCheckConnect(unittest.TestCase):
    """
    Unit tests for CheckConnect class in checkconnect/cli/checkconnect.py.

    This test suite verifies the functionality of the CheckConnect class,
    which is responsible for managing network connectivity checks and report generation.
    """

    def setUp(self):
        """
        Set up test fixtures before each test method.

        This includes:
        - Creating a config parser with test settings
        - Initializing a CheckConnect instance
        - Setting up a mock logger
        - Configuring translation handling
        """
        # Create test configuration
        self.config_parser = configparser.ConfigParser()
        self.config_parser["Files"] = {
            "ntp_servers": "ntp_servers.csv",
            "urls": "urls.csv",
        }
        self.config_parser["Output"] = {"directory": "reports"}
        self.config_parser["Network"] = {"timeout": "5"}

        # Create CheckConnect instance
        self.check_connect = CheckConnect(self.config_parser, "output.txt")

        # Set up mock logger
        self.mock_logger = MockLogger()
        self.check_connect.logger = self.mock_logger

        # Translation setup
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "checkconnect",
            "cli",
            "locales",
        )

        try:
            self.translate = gettext.translation(
                self.TRANSLATION_DOMAIN,
                self.LOCALES_PATH,
                languages=[os.environ.get("LANG", "en")],
            ).gettext
        except FileNotFoundError:
            # Fallback to a simple identity function
            self.translate = lambda message: message

    def tearDown(self):
        """
        Clean up after each test.
        """
        # Reset the mock logger between tests
        self.mock_logger.reset()

    def test_checkconnect_initialization(self):
        """
        Test that CheckConnect initializes correctly with the provided configuration.

        Verifies that class attributes are properly set from the config parser
        and default values are correctly applied.
        """
        self.assertIsInstance(self.check_connect, CheckConnect)
        self.assertEqual(self.check_connect.config_parser, self.config_parser)
        self.assertEqual(self.check_connect.output_file, "output.txt")
        self.assertEqual(self.check_connect.ntp_file, "ntp_servers.csv")
        self.assertEqual(self.check_connect.url_file, "urls.csv")
        self.assertEqual(self.check_connect.report_dir, "reports")

    def test_checkconnect_initialization_with_defaults(self):
        """
        Test that CheckConnect uses default values correctly when config options are missing.

        This test uses a minimal config and verifies that the class falls back to
        the specified default values for missing options.
        """
        # Create a minimal config
        minimal_config = configparser.ConfigParser()

        # Initialize with minimal config
        check_connect = CheckConnect(minimal_config)

        # Verify defaults are used
        self.assertEqual(check_connect.ntp_file, "ntp_servers.csv")  # Default value
        self.assertEqual(check_connect.url_file, "urls.csv")  # Default value
        self.assertEqual(check_connect.report_dir, "reports")  # Default value
        self.assertIsNone(check_connect.output_file)  # Default is None

    @patch("checkconnect.core.ntp_checker.NTPChecker.check_ntp_servers")
    @patch("checkconnect.core.url_checker.URLChecker.check_urls")
    def test_run_success(self, mock_check_urls, mock_check_ntp_servers):
        """
        Test successful execution of the run method.

        This test verifies that when everything works correctly:
        - The NTPChecker and URLChecker methods are called with correct arguments
        - Appropriate log messages are generated
        """
        # Mock the checker methods to return successful results
        mock_check_ntp_servers.return_value = ["NTP server result"]
        mock_check_urls.return_value = ["URL check result"]

        # Call the run method
        self.check_connect.run()

        # Verify the checkers were called with correct arguments
        mock_check_ntp_servers.assert_called_once_with("ntp_servers.csv", "output.txt")
        mock_check_urls.assert_called_once_with("urls.csv", "output.txt")

        # Verify log messages
        self.assertIn(
            self.translate("Starting CheckConnect..."),
            self.mock_logger.infos,
        )
        self.assertIn(
            self.translate("Tests completed successfully."),
            self.mock_logger.infos,
        )

    @patch("checkconnect.core.ntp_checker.NTPChecker.check_ntp_servers")
    @patch("checkconnect.core.url_checker.URLChecker.check_urls")
    def test_run_with_custom_files(self, mock_check_urls, mock_check_ntp_servers):
        """
        Test that the run method respects custom file paths when provided.

        This test verifies that when custom file paths are provided to the run method,
        they are passed to the checker methods instead of the default paths.
        """
        # Mock the checker methods
        mock_check_ntp_servers.return_value = ["NTP server result"]
        mock_check_urls.return_value = ["URL check result"]

        # Call run with custom file paths
        self.check_connect.run("custom_ntp.csv", "custom_urls.csv")

        # Verify the checkers were called with the custom file paths
        mock_check_ntp_servers.assert_called_once_with("custom_ntp.csv", "output.txt")
        mock_check_urls.assert_called_once_with("custom_urls.csv", "output.txt")

    @patch(
        "checkconnect.core.ntp_checker.NTPChecker.check_ntp_servers",
        side_effect=FileNotFoundError("NTP file not found"),
    )
    @patch("checkconnect.core.url_checker.URLChecker.check_urls")
    def test_run_file_not_found_error(self, mock_check_urls, mock_check_ntp_servers):
        """
        Test the run method correctly handles and propagates FileNotFoundError.

        This test verifies that when a FileNotFoundError occurs during execution,
        it is logged and re-raised to the caller.
        """
        # Call run and expect a FileNotFoundError to be raised
        with self.assertRaises(FileNotFoundError):
            self.check_connect.run()

        # Verify log messages
        self.assertIn(
            self.translate("Starting CheckConnect..."),
            self.mock_logger.infos,
        )
        self.assertIn(
            self.translate("File not found: NTP file not found"),
            self.mock_logger.errors,
        )

        # Verify URL checker was not called after NTP checker failed
        mock_check_urls.assert_not_called()

    @patch("checkconnect.core.ntp_checker.NTPChecker.check_ntp_servers")
    @patch(
        "checkconnect.core.url_checker.URLChecker.check_urls",
        side_effect=Exception("URL check error"),
    )
    def test_run_generic_exception(self, mock_check_urls, mock_check_ntp_servers):
        """
        Test the run method correctly handles and propagates generic exceptions.

        This test verifies that when a generic exception occurs during execution,
        it is logged and re-raised to the caller.
        """
        # Call run and expect an Exception to be raised
        with self.assertRaises(Exception) as context:
            self.check_connect.run()

        # Verify the exception details
        self.assertEqual(str(context.exception), "URL check error")

        # Verify log messages
        self.assertIn(
            self.translate("Starting CheckConnect..."),
            self.mock_logger.infos,
        )
        self.assertIn(
            self.translate("Error during tests: URL check error"),
            "".join(self.mock_logger.exceptions),
        )

    def test_generate_reports_success(self):
        """
        Test successful execution of the generate_reports method.

        This test ensures that when the generate_reports method runs successfully:
        1. The correct report generation functions are called with proper arguments
        2. Appropriate log messages are generated
        """
        # First, we need to effectively patch the core functions being used
        with (
            patch("checkconnect.cli.checkconnect.create_pdf_report") as mock_pdf,
            patch("checkconnect.cli.checkconnect.create_html_report") as mock_html,
        ):

            # Call the method under test
            self.check_connect.generate_reports()

            # Verify both report functions were called with correct parameters
            mock_pdf.assert_called_once_with("ntp_servers.csv", "urls.csv", "reports")
            mock_html.assert_called_once_with("ntp_servers.csv", "urls.csv", "reports")

            # Verify the expected log messages were generated
            self.assertIn(
                self.translate("Starting report generation..."),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate("Reports generated successfully."),
                self.mock_logger.infos,
            )

    def test_generate_reports_with_custom_files(self):
        """
        Test that generate_reports properly uses custom file paths when provided.

        This test verifies that when custom file paths are supplied to generate_reports:
        1. The report generation functions are called with these custom paths
        2. The default paths are overridden correctly
        """
        with (
            patch("checkconnect.cli.checkconnect.create_pdf_report") as mock_pdf,
            patch("checkconnect.cli.checkconnect.create_html_report") as mock_html,
        ):

            # Call with custom file paths
            custom_ntp = "custom_ntp.csv"
            custom_url = "custom_urls.csv"
            self.check_connect.generate_reports(custom_ntp, custom_url)

            # Verify custom paths were used
            mock_pdf.assert_called_once_with(custom_ntp, custom_url, "reports")
            mock_html.assert_called_once_with(custom_ntp, custom_url, "reports")

    def test_generate_reports_pdf_exception(self):
        """
        Test exception handling during PDF report generation.

        This test ensures that when PDF generation fails:
        1. The exception is caught and logged properly
        2. HTML generation is not attempted
        3. The method doesn't propagate the exception
        """
        # Simulate a PDF generation failure
        pdf_error = Exception("PDF creation error")
        with (
            patch(
                "checkconnect.cli.checkconnect.create_pdf_report",
                side_effect=pdf_error,
            ) as mock_pdf,
            patch("checkconnect.cli.checkconnect.create_html_report") as mock_html,
        ):

            # Call the method - should not raise an exception
            self.check_connect.generate_reports()

            # Verify error handling
            self.assertIn(
                self.translate("Starting report generation..."),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate(f"Error while generating reports: {pdf_error}"),
                "".join(self.mock_logger.exceptions),
            )

            # HTML generation should not be attempted after PDF failure
            mock_html.assert_not_called()

    def test_generate_reports_html_exception(self):
        """
        Test exception handling during HTML report generation.

        This test ensures that when HTML generation fails:
        1. The exception is caught and logged properly
        2. PDF generation is completed before the HTML error
        3. The method doesn't propagate the exception
        """
        # Simulate HTML generation failure
        html_error = Exception("HTML creation error")
        with (
            patch("checkconnect.cli.checkconnect.create_pdf_report") as mock_pdf,
            patch(
                "checkconnect.cli.checkconnect.create_html_report",
                side_effect=html_error,
            ) as mock_html,
        ):

            # Call the method - should not raise an exception
            self.check_connect.generate_reports()

            # Verify error handling
            self.assertIn(
                self.translate("Starting report generation..."),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate(f"Error while generating reports: {html_error}"),
                "".join(self.mock_logger.exceptions),
            )

            # PDF should still be generated successfully
            mock_pdf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
