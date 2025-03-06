# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
CheckConnect GUI: A graphical user interface for network connectivity checks.

This module provides a `CheckConnectGUI` class that allows users to:
- Run NTP and URL connectivity tests via a graphical interface.
- Select input files using a file browser.
- View real-time test logs in a GUI output window.
- Generate reports in PDF and HTML format.
"""

import configparser
import gettext
import locale
import logging
import os
from typing import Optional

from PySide6.QtCore import QLocale, QTranslator
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from checkconnect import __about__
from checkconnect.core.create_reports import (
    ReportGenerator,
    create_html_report,
    create_pdf_report,
)
from checkconnect.core.ntp_checker import NTPChecker
from checkconnect.core.url_checker import URLChecker

# Define the translation domain
TRANSLATION_DOMAIN = "checkconnect"

# Set the locales path relative to the current file
LOCALES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "gui",
    "locales",
)


# Function to get the current locale
def get_system_locale():
    try:
        return locale.getlocale()[0] or locale.getdefaultlocale()[0]
    except:
        return "en_US"  # Fallback


class CheckConnectGUI(QWidget):
    """
    Graphical User Interface (GUI) for CheckConnect.

    This class provides the main window and logic for the CheckConnect GUI application.
    It allows users to select NTP and URL files, run connectivity tests, and generate reports.
    """

    def __init__(
        self,
        config_parser: configparser.ConfigParser,
        output_file: Optional[str] = None,
        logger: logging.Logger = None,
    ):
        """
        Initializes the CheckConnectGUI instance.

        Args:
        ----
            config_parser (configparser.ConfigParser): The configuration parser containing the settings.
            output_file (Optional[str], optional): The path to the output file. Defaults to None.
            logger (logging.Logger, optional): A logger instance. If None, a default logger is created.

        """
        super().__init__()
        self.config_parser = config_parser
        self.output_file = output_file
        self.logger = logger or logging.getLogger(__name__)  # Instance logger
        self.url_checker = URLChecker(
            config_parser,
            logger=self.logger,
        )  # Pass the logger
        self.ntp_checker = NTPChecker(
            config_parser,
            logger=self.logger,
        )  # Pass the logger
        self.report_dir = self.config_parser.get(
            "Output",
            "directory",
            fallback="reports",
        )
        self.ntp_file = self.config_parser.get(
            "Files",
            "ntp_servers",
            fallback="ntp_servers.csv",
        )
        self.url_file = self.config_parser.get("Files", "urls", fallback="urls.csv")

        self.translator = QTranslator()  # Create the Translator

        # Load Translation
        self.load_translation()

        self.setup_gui()

    def load_translation(self):
        """
        Loads the translation file based on the system locale.
        """
        app = QApplication.instance()
        system_locale = get_system_locale()

        # Get the locale code (e.g., "de_DE")
        locale_code = QLocale(system_locale).name()

        # Construct the translation file path
        translation_file = os.path.join(LOCALES_PATH, f"checkconnect_{locale_code}.qm")

        if os.path.exists(translation_file):
            # Load the translation file
            self.translator.load(translation_file)

            # Install the translator
            app.installTranslator(self.translator)
            self.logger.info(f"Translation loaded for locale: {locale_code}")
        else:
            self.logger.warning(f"Translation file not found for locale: {locale_code}")

    def tr(self, source_text):
        """
        A simple translation method.
        """
        return QApplication.translate("CheckConnectGUI", source_text)

    def setup_gui(self):
        """
        Creates and configures the GUI layout.

        This method creates all the necessary widgets and layouts for the GUI, including:
            - File selection inputs for NTP and URL files.
            - Buttons to trigger NTP and URL tests, report generation, and application exit.
            - An output log to display real-time test results.
        """
        self.setWindowTitle(
            self.tr(f"CheckConnect GUI - Version {__about__.__version__}"),
        )  # Set title with version

        # Create layout
        layout = QVBoxLayout()

        # NTP File Selection
        ntp_layout = QHBoxLayout()
        ntp_label = QLabel(self.tr("Select NTP CSV File:"))
        self.ntp_input = QLineEdit(self.ntp_file)  # Set default from ConfigFile
        ntp_browse_button = QPushButton(self.tr("Browse"))
        ntp_browse_button.clicked.connect(self.browse_ntp_file)
        ntp_layout.addWidget(ntp_label)
        ntp_layout.addWidget(self.ntp_input)
        ntp_layout.addWidget(ntp_browse_button)
        layout.addLayout(ntp_layout)

        # URL File Selection
        url_layout = QHBoxLayout()
        url_label = QLabel(self.tr("Select URL CSV File:"))
        self.url_input = QLineEdit(self.url_file)  # Set default from ConfigFile
        url_browse_button = QPushButton(self.tr("Browse"))
        url_browse_button.clicked.connect(self.browse_url_file)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(url_browse_button)
        layout.addLayout(url_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.ntp_button = QPushButton(self.tr("Test NTP"))
        self.ntp_button.clicked.connect(self.test_ntp)
        self.url_button = QPushButton(self.tr("Test URLs"))
        self.url_button.clicked.connect(self.test_urls)
        self.report_button = QPushButton(self.tr("Generate Report"))
        self.report_button.clicked.connect(self.create_reports)
        exit_button = QPushButton(self.tr("Exit"))
        exit_button.clicked.connect(self.close)

        button_layout.addWidget(self.ntp_button)
        button_layout.addWidget(self.url_button)
        button_layout.addWidget(self.report_button)
        button_layout.addWidget(exit_button)
        layout.addLayout(button_layout)

        # Output Log
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        layout.addWidget(self.output_log)

        self.setLayout(layout)

    def browse_ntp_file(self):
        """
        Opens a file dialog to select the NTP CSV file.

        Updates the `ntp_input` QLineEdit and `ntp_file` attribute with the selected file path.
        """
        file_name, _ = QFileDialog.getOpenFileName(self, self.tr("Select NTP CSV File"))
        if file_name:
            self.ntp_input.setText(file_name)
            self.ntp_file = file_name

    def browse_url_file(self):
        """
        Opens a file dialog to select the URL CSV file.

        Updates the `url_input` QLineEdit and `url_file` attribute with the selected file path.
        """
        file_name, _ = QFileDialog.getOpenFileName(self, self.tr("Select URL CSV File"))
        if file_name:
            self.url_input.setText(file_name)
            self.url_file = file_name

    def test_ntp(self):
        """
        Runs NTP connectivity tests.

        Retrieves the NTP file path from the `ntp_input` QLineEdit, performs validation,
        and executes the NTP tests using the `NTPChecker`. The test results are displayed
        in the `output_log` QTextEdit.
        """
        ntp_file = self.ntp_input.text()
        if not ntp_file or not os.path.exists(ntp_file):
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Invalid or missing NTP file selected."),
            )
            return

        self.output_log.append(self.tr("Running NTP tests...\n"))
        results = self.ntp_checker.check_ntp_servers(ntp_file, self.output_file)
        for result in results:
            self.output_log.append(result + "\n")
        self.output_log.append(self.tr("NTP tests completed.\n"))

    def test_urls(self):
        """
        Runs URL connectivity tests.

        Retrieves the URL file path from the `url_input` QLineEdit, performs validation,
        and executes the URL tests using the `URLChecker`. The test results are displayed
        in the `output_log` QTextEdit.
        """
        url_file = self.url_input.text()
        if not url_file or not os.path.exists(url_file):
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Invalid or missing URL file selected."),
            )
            return

        self.output_log.append(self.tr("Running URL tests...\n"))
        results = self.url_checker.check_urls(url_file, self.output_file)
        for result in results:
            self.output_log.append(result + "\n")
        self.output_log.append(self.tr("URL tests completed.\n"))

    def create_reports(self):
        """
        Generates PDF and HTML reports from test results.

        Retrieves the NTP and URL file paths from the `ntp_input` and `url_input` QLineEdits,
        performs validation, and generates the reports using the `create_pdf_report` and
        `create_html_report` functions. A success or error message is displayed in a QMessageBox.
        """
        ntp_file = self.ntp_input.text()
        url_file = self.url_input.text()

        if (
            not ntp_file
            or not os.path.exists(ntp_file)
            or not url_file
            or not os.path.exists(url_file)
        ):
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("Invalid or missing files for report generation."),
            )
            return

        try:
            create_pdf_report(ntp_file, url_file, self.report_dir)
            create_html_report(ntp_file, url_file, self.report_dir)
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr("Reports generated successfully."),
            )
            self.output_log.append(self.tr("Reports generated successfully.\n"))
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr(f"Error generating reports: {e}"),
            )
            self.logger.exception("Error generating reports.")
