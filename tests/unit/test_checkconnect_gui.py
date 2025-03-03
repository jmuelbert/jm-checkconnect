# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, call, patch

from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QTextEdit, QWidget

from checkconnect.gui.checkconnect_gui import CheckConnectGUI
from tests.utils import MockLogger


class TestCheckConnectGUI(unittest.TestCase):
    """Unit tests for CheckConnectGUI class in checkconnect/gui/checkconnect_gui.py."""

    @classmethod
    def setUpClass(cls):
        """
        Create a QApplication instance for all tests in this class.

        PySide6 applications require a QApplication instance to be running.
        This method ensures that one exists before any tests are run.  It is called
        once before all tests.
        """
        # Check if QApplication already exists
        if not QApplication.instance():
            cls.app = QApplication([])
            cls.created_app = True
        else:
            cls.app = QApplication.instance()
            cls.created_app = False

    @classmethod
    def tearDownClass(cls):
        """
        Clean up QApplication instance after all tests have run.

        This method quits the QApplication instance, releasing resources. It is
        called once after all tests.
        """
        # Only quit if we created the app
        if cls.created_app:
            cls.app.quit()

    def setUp(self):
        """
        Set up for each test method.

        This includes:
            - Creating a config parser.
            - Initializing CheckConnectGUI with the config parser.
            - Creating a MockLogger instance.
            - Assigning the MockLogger to the GUI.
            - Mocking the `append` method of the GUI's output log.
            - Resetting the MockLogger to ensure a clean slate for each test.
        """
        self.config_parser = configparser.ConfigParser()
        self.config_parser["Files"] = {"ntp_servers": "ntp_servers.csv", "urls": "urls.csv"}
        self.config_parser["Output"] = {"directory": "reports"}

        self.gui = CheckConnectGUI(self.config_parser, "output.txt")
        self.mock_logger = MockLogger()
        self.gui.logger = self.mock_logger  # Assign mock logger
        self.gui.output_log.append = MagicMock() #Mock the methode from gui
        self.mock_logger.reset()

        # Translation setup
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'checkconnect', 'gui', 'locales')

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

    def test_checkconnect_gui_initialization(self):
        """
        Test CheckConnectGUI initializes correctly.

        Checks that the GUI is instantiated correctly with the provided config parser and output file,
        and verifies that the relevant class attributes are set to the expected values. Also verifies that the
        GUI widgets are created as instances of their respective Qt classes.
        """
        self.assertIsInstance(self.gui, CheckConnectGUI)
        self.assertEqual(self.gui.config_parser, self.config_parser)
        self.assertEqual(self.gui.output_file, "output.txt")
        self.assertEqual(self.gui.ntp_file, "ntp_servers.csv")
        self.assertEqual(self.gui.url_file, "urls.csv")
        self.assertEqual(self.gui.report_dir, "reports")
        self.assertIsInstance(self.gui.url_input, QLineEdit)  # Check if widgets are created
        self.assertIsInstance(self.gui.output_log, QTextEdit)

    @patch("checkconnect.gui.checkconnect_gui.QFileDialog.getOpenFileName", return_value=("new_ntp.csv", ""))
    def test_browse_ntp_file(self, mock_getOpenFileName):
        """
        Test browse_ntp_file method.

        This test mocks the QFileDialog.getOpenFileName method to simulate a user selecting a new NTP file.
        It then checks that the GUI's ntp_input text field is updated with the selected file name and that
        the GUI's ntp_file attribute is also updated.
        """
        self.gui.browse_ntp_file()
        self.assertEqual(self.gui.ntp_input.text(), "new_ntp.csv")
        self.assertEqual(self.gui.ntp_file, "new_ntp.csv")

    @patch("checkconnect.gui.checkconnect_gui.QFileDialog.getOpenFileName", return_value=("new_url.csv", ""))
    def test_browse_url_file(self, mock_getOpenFileName):
        """
        Test browse_url_file method.

        This test mocks the QFileDialog.getOpenFileName method to simulate a user selecting a new URL file.
        It then checks that the GUI's url_input text field is updated with the selected file name and that
        the GUI's url_file attribute is also updated.
        """
        self.gui.browse_url_file()
        self.assertEqual(self.gui.url_input.text(), "new_url.csv")
        self.assertEqual(self.gui.url_file, "new_url.csv")

    @patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=True)
    @patch("checkconnect.core.ntp_checker.NTPChecker.check_ntp_servers")
    def test_test_ntp_success(self, mock_check_ntp_servers, mock_path_exists):
        """
        Test test_ntp method success.

        This test mocks the os.path.exists and NTPChecker.check_ntp_servers methods to simulate a successful
        NTP test run. It sets the ntp_input text field to a valid file name, calls the test_ntp method, and then
        checks that the check_ntp_servers method is called with the correct arguments and that the output log
        is updated with the expected messages.
        """
        mock_check_ntp_servers.return_value = ["NTP Result 1", "NTP Result 2"]

        self.gui.ntp_input.setText("ntp_servers.csv")  # Set input file
        self.gui.test_ntp()

        mock_check_ntp_servers.assert_called_once_with("ntp_servers.csv", "output.txt")
        expected_log_calls = [
            call(self.translate("Running NTP tests...\n")),
            call("NTP Result 1\n"),
            call("NTP Result 2\n"),
            call(self.translate("NTP tests completed.\n")),
        ]
        self.assertEqual(self.gui.output_log.append.mock_calls, expected_log_calls) #Check that the messages was sended to the gui-log

    @patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=False)
    @patch("checkconnect.gui.checkconnect_gui.QMessageBox.critical")
    def test_test_ntp_file_not_found(self, mock_critical, mock_path_exists):
        """
        Test test_ntp method file not found.

        This test mocks the os.path.exists and QMessageBox.critical methods to simulate a scenario where the
        selected NTP file does not exist. It sets the ntp_input text field to an invalid file name, calls the
        test_ntp method, and then checks that the critical message box is displayed with the expected message.
        """
        self.gui.ntp_input.setText("invalid_ntp.csv")  # Set invalid input file
        self.gui.test_ntp()

        mock_critical.assert_called_once_with(self.gui, self.translate("Error"), self.translate("Invalid or missing NTP file selected."))

    @patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=True)
    @patch("checkconnect.core.url_checker.URLChecker.check_urls")
    def test_test_urls_success(self, mock_check_urls, mock_path_exists):
        """
        Test test_urls method success.

        This test mocks the os.path.exists and URLChecker.check_urls methods to simulate a successful
        URL test run. It sets the url_input text field to a valid file name, calls the test_urls method, and then
        checks that the check_urls method is called with the correct arguments and that the output log
        is updated with the expected messages.
        """
        mock_check_urls.return_value = ["URL Result 1", "URL Result 2"]

        self.gui.url_input.setText("urls.csv")  # Set input file
        self.gui.test_urls()

        mock_check_urls.assert_called_once_with("urls.csv", "output.txt")
        expected_log_calls = [
            call(self.translate("Running URL tests...\n")),
            call("URL Result 1\n"),
            call("URL Result 2\n"),
            call(self.translate("URL tests completed.\n")),
        ]
        self.assertEqual(self.gui.output_log.append.mock_calls, expected_log_calls)  # Check that the messages was sended to the gui-log

    @patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=False)
    @patch("checkconnect.gui.checkconnect_gui.QMessageBox.critical")
    def test_test_urls_file_not_found(self, mock_critical, mock_path_exists):
        """
        Test test_urls method file not found.

        This test mocks the os.path.exists and QMessageBox.critical methods to simulate a scenario where the
        selected URL file does not exist. It sets the url_input text field to an invalid file name, calls the
        test_urls method, and then checks that the critical message box is displayed with the expected message.
        """
        self.gui.url_input.setText("invalid_urls.csv")  # Set invalid input file
        self.gui.test_urls()

        mock_critical.assert_called_once_with(self.gui, self.translate("Error"), self.translate("Invalid or missing URL file selected."))

    @patch("checkconnect.gui.checkconnect_gui.create_pdf_report")  # Changed path to match import
    @patch("checkconnect.gui.checkconnect_gui.create_html_report")  # Changed path to match import
    @patch("checkconnect.gui.checkconnect_gui.QMessageBox.information")
    def test_create_reports_success(self, mock_information, mock_create_html_report, mock_create_pdf_report):
        """
        Test create_reports method success.

        This test mocks the create_pdf_report, create_html_report, and QMessageBox.information
        methods to simulate a successful report generation. It sets the ntp_input and url_input text fields to valid
        file names, calls the create_reports method, and then checks that the create_pdf_report and create_html_report
        methods are called with the correct arguments and that the information message box is displayed with the
        expected message.
        """
        # Mock os.path.exists to always return True for file checks
        with patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=True):
            mock_create_pdf_report.return_value = None
            mock_create_html_report.return_value = None

            self.gui.ntp_input.setText("ntp_servers.csv")  # Set input files
            self.gui.url_input.setText("urls.csv")
            self.gui.create_reports()

            mock_create_pdf_report.assert_called_once_with("ntp_servers.csv", "urls.csv", "reports")
            mock_create_html_report.assert_called_once_with("ntp_servers.csv", "urls.csv", "reports")
            mock_information.assert_called_once_with(self.gui, self.translate("Success"), self.translate("Reports generated successfully."))
            self.assertEqual(self.gui.output_log.append.mock_calls, [call(self.translate("Reports generated successfully.\n"))])

    @patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=False)
    @patch("checkconnect.gui.checkconnect_gui.QMessageBox.critical")
    def test_create_reports_file_not_found(self, mock_critical, mock_path_exists):
        """
        Test create_reports method file not found.

        This test mocks the os.path.exists and QMessageBox.critical methods to simulate a scenario where either the
        NTP or URL file does not exist. It sets the ntp_input and url_input text fields to invalid file names,
        calls the create_reports method, and then checks that the critical message box is displayed with the
        expected message.
        """
        self.gui.ntp_input.setText("invalid_ntp.csv")
        self.gui.url_input.setText("invalid_urls.csv")
        self.gui.create_reports()

        mock_critical.assert_called_once_with(self.gui, self.translate("Error"), self.translate("Invalid or missing files for report generation."))

    @patch("checkconnect.gui.checkconnect_gui.create_pdf_report", side_effect=Exception("Report error"))  # Changed path to match import
    @patch("checkconnect.gui.checkconnect_gui.QMessageBox.critical")
    def test_create_reports_exception(self, mock_critical, mock_create_pdf_report):
        """
        Test create_reports method exception.

        This test mocks the create_pdf_report and QMessageBox.critical methods to simulate a scenario where
        an exception occurs during report generation (specifically, during PDF creation). It sets the ntp_input and url_input
        text fields to valid file names, calls the create_reports method, and then checks that the critical message box
        is displayed with the expected error message.
        """
        # Mock os.path.exists to always return True for file checks
        with patch("checkconnect.gui.checkconnect_gui.os.path.exists", return_value=True):
            self.gui.ntp_input.setText("ntp_servers.csv")
            self.gui.url_input.setText("urls.csv")
            self.gui.create_reports()
            mock_critical.assert_called_once_with(self.gui, self.translate("Error"), self.translate("Error generating reports: Report error"))
