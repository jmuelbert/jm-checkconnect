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

import logging
import os

from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget)

from checkconnect.core.create_reports import (create_html_report,
                                              create_pdf_report)
from checkconnect.core.ntp_checker import test_ntp
from checkconnect.core.url_checker import test_urls


class CheckConnectGUI(QWidget):
    """
    Graphical User Interface (GUI) for CheckConnect.

    This class provides a simple GUI using PySide6 to perform network checks
    and generate reports.
    """

    def __init__(self, config_file: str = None, output_file: str = None):
        """
        Initializes the CheckConnectGUI instance.

        Args:
            config_file (str, optional): Path to a configuration file. Defaults to None.
            output_file (str, optional): Path to an output file. Defaults to None.
        """
        super().__init__()
        self.config_file = config_file
        self.output_file = output_file
        self.setup_logging()
        self.setup_gui()

    def setup_logging(self):
        """Configures logging for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("CheckConnect")

    def setup_gui(self):
        """Creates and configures the GUI layout."""
        self.setWindowTitle("CheckConnect GUI")

        # Create layout
        layout = QVBoxLayout()

        # NTP File Selection
        ntp_layout = QHBoxLayout()
        ntp_label = QLabel("Select NTP CSV File:")
        self.ntp_input = QLineEdit()
        ntp_browse_button = QPushButton("Browse")
        ntp_browse_button.clicked.connect(self.browse_ntp_file)
        ntp_layout.addWidget(ntp_label)
        ntp_layout.addWidget(self.ntp_input)
        ntp_layout.addWidget(ntp_browse_button)
        layout.addLayout(ntp_layout)

        # URL File Selection
        url_layout = QHBoxLayout()
        url_label = QLabel("Select URL CSV File:")
        self.url_input = QLineEdit()
        url_browse_button = QPushButton("Browse")
        url_browse_button.clicked.connect(self.browse_url_file)
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(url_browse_button)
        layout.addLayout(url_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.ntp_button = QPushButton("Test NTP")
        self.ntp_button.clicked.connect(self.test_ntp)
        self.url_button = QPushButton("Test URLs")
        self.url_button.clicked.connect(self.test_urls)
        self.report_button = QPushButton("Generate Report")
        self.report_button.clicked.connect(self.create_reports)
        exit_button = QPushButton("Exit")
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
        """Opens a file dialog to select the NTP CSV file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select NTP CSV File")
        if file_name:
            self.ntp_input.setText(file_name)

    def browse_url_file(self):
        """Opens a file dialog to select the URL CSV file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select URL CSV File")
        if file_name:
            self.url_input.setText(file_name)

    def test_ntp(self):
        """Runs NTP connectivity tests."""
        ntp_file = self.ntp_input.text()
        if not ntp_file or not os.path.exists(ntp_file):
            QMessageBox.critical(self, "Error", "Invalid or missing NTP file selected.")
            return

        self.output_log.append("Running NTP tests...\n")
        test_ntp(ntp_file, self.output_file)
        self.output_log.append("NTP tests completed.\n")

    def test_urls(self):
        """Runs URL connectivity tests."""
        url_file = self.url_input.text()
        if not url_file or not os.path.exists(url_file):
            QMessageBox.critical(self, "Error", "Invalid or missing URL file selected.")
            return

        self.output_log.append("Running URL tests...\n")
        test_urls(url_file, self.output_file)
        self.output_log.append("URL tests completed.\n")

    def create_reports(self):
        """Generates PDF and HTML reports from test results."""
        ntp_file = self.ntp_input.text()
        url_file = self.url_input.text()

        if not ntp_file or not os.path.exists(ntp_file) or not url_file or not os.path.exists(url_file):
            QMessageBox.critical(self, "Error", "Invalid or missing files for report generation.")
            return

        create_pdf_report(ntp_file, url_file)
        create_html_report(ntp_file, url_file)
        QMessageBox.information(self, "Success", "Reports generated successfully.")
        self.output_log.append("Reports generated successfully.\n")


if __name__ == "__main__":
    import sys

    # Start the GUI application
    app = QApplication(sys.argv)
    window = CheckConnectGUI()
    window.show()
    sys.exit(app.exec())

