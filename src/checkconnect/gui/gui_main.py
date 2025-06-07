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

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from checkconnect import __about__
from checkconnect.core.checkconnect import CheckConnect
from checkconnect.reports.report_generator import (
    generate_html_report,
    generate_pdf_report,
)
from checkconnect.reports.report_manager import OutputFormat, ReportManager

if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext

log = structlog.get_logger(__name__)

class CheckConnectGUIRunner(QWidget):
    """
    Graphical User Interface (GUI) for CheckConnect.

    This class provides the main window and logic for the CheckConnect GUI application.
    It allows users to select NTP and URL files, run connectivity tests, and generate reports.
    """

    def __init__(
        self,
        context: AppContext,
        language: str | None = None,
    ) -> None:
        """
        Initialize the CheckConnectGUI.

        Initialize the CheckConnectGUI with configuration,
        output file, and logger.

        Args:
        ----
            context (AppContext): Shared application context that includes
                                    logger, translator, and other shared resources.


        """
        super().__init__()

        self.context = context
        self.logger = log
        self.translator = context.translator
        self._ = context.gettext
        self.config = context.config  # For translations of UI text, if necessary
        self.settings = QSettings("JM", "CheckConnect")
        self.language = language
        self.checkconnect = CheckConnect(context)

        self.setup_gui()

    def tr(self, source_text: str) -> str:
        """Implement Simple translation method."""
        return QApplication.translate("CheckConnectGUI", source_text)

    def setup_gui(self) -> None:
        """
        Create and configures the GUI layout.

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

        layout.addWidget(self.create_buttons())
        layout.addWidget(self.create_output_log())

        self.setLayout(layout)

    def create_buttons(self) -> QWidget:
        """
        Create a horizontal layout for the action buttons.

        Returns
        -------
            A QWidget containing the "Test NTP", "Test URLs",
            "Generate Report", and "Exit" buttons.

        """
        button_widget = QWidget()  # Create a QWidget to hold the buttons
        layout = QHBoxLayout(button_widget)

        # Buttons
        self.ntp_button = QPushButton(self.tr("Test NTP"))
        self.ntp_button.clicked.connect(self.test_ntp)
        self.url_button = QPushButton(self.tr("Test URLs"))
        self.url_button.clicked.connect(self.test_urls)
        self.report_button = QPushButton(self.tr("Generate Report"))
        self.report_button.clicked.connect(self.generate_reports)
        self.summary_button = QPushButton(self.tr("Show summary"))
        self.format_selector = QComboBox()
        self.format_selector.addItems(["text", "markdown", "html"])
        self.format_selector.currentIndexChanged.connect(self.show_summary)
        self.summary_button.clicked.connect(self.show_summary)
        self.summary_view = QTextBrowser()
        exit_button = QPushButton(self.tr("Exit"))
        exit_button.clicked.connect(self.close)

        for btn in [
            self.ntp_button,
            self.url_button,
            self.report_button,
            self.summary_button,
            self.format_selector,
            self.summary_view,
            exit_button,
        ]:
            layout.addWidget(btn)

        button_widget.setLayout(layout)  # Set the layout for the QWidget

        return button_widget

    def create_output_log(self) -> QTextEdit:
        """
        Create the QTextEdit widget for displaying output logs.

        Returns
        -------
            A QTextEdit widget configured as read-only and with a placeholder text.

        """
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setPlaceholderText(self._("Results and logs will appear here…"))
        return self.output_log

    def test_ntp(self) -> None:
        """
        Test the NTP servers specified in the configuration.

        Logs the results of the NTP tests to the output log.
        """
        self.log_output(self._("Running NTP tests…"))

        self.log_output(self.tr("Running NTP tests…"))
        try:
            self.checkconnect.run_ntp_checks()
            for line in self.checkconnect.ntp_results or []:
                self.log_output(line)
            self.ntp_results = self.checkconnect.ntp_results or []
        except Exception as e:
            self.logger.exception(self._("Error in test_ntp"))
            self.show_error(self.tr(f"NTP test failed: {e}"))
        else:
            self.log_output(self.tr("NTP tests completed."))

    def test_urls(self) -> None:
        """
        Tests the URLs specified in the configuration.

        Logs the results of the URL tests to the output log.
        """
        self.log_output(self._("Running URL tests…"))

        try:
            self.checkconnect.run_url_checks()
            for line in self.checkconnect.url_results or []:
                self.log_output(line)
            self.url_results = self.checkconnect.url_results or []
        except Exception as e:
            self.logger.exception(self._("Error in test_urls"))
            self.show_error(self.tr(f"URL test failed: {e}"))
        else:
            self.log_output(self.tr("URL tests completed."))

    def generate_reports(self) -> None:
        """
        Generate HTML and PDF reports.

        Displays an error message if report generation fails.
        Logs a success message to the output log upon successful report generation.
        """
        try:
            generate_html_report(
                context=self.context,
                ntp_results=self.checkconnect.ntp_results,
                url_results=self.checkconnect.url_results,
            )

            generate_pdf_report(
                context=self.context,
                ntp_results=self.checkconnect.ntp_results,
                url_results=self.checkconnect.url_results,
            )

        except Exception as e:
            self.logger.exception("Error generating reports.")
            self.show_error(self.tr(f"Failed to generate reports: {e}"))
        else:
            self.log_output(self._("Reports generated successfully."))

    def log_output(self, message: str) -> None:
        """
        Create the output log widget.

        Returns
        -------
            QTextEdit: A read-only text field to display test results and logs.

        """
        self.output_log.append(message)
        self.logger.info(message)

    def show_summary(self) -> None:
        """
        Run connectivity checks and displays a formatted summary in the GUI.

        This method performs both URL and NTP connectivity checks using the CheckConnect
        instance. It then generates a summary in the user-selected format (plain text,
        Markdown, or HTML) and displays it in the QTextBrowser widget. If the selected
        format is HTML, the summary is rendered as rich text; otherwise, it is shown
        as plain text. Errors during the process are logged and shown to the user via
        a message box.

        Raises
        ------
            Displays a QMessageBox with the error message if any exceptions occur.

        """
        try:
            format_ = self.format_selector.currentText()
            manager = ReportManager.from_context(context=self.context)
            ntp_results, url_results = manager.load_previous_results()
            if format_ == "html":
                summary = manager.get_summary(
                    ntp_results=ntp_results,
                    url_results=url_results,
                    summary_format=OutputFormat.html,
                )
                self.summary_view.setHtml(summary)
                self.log_output(self.tr("HTML summary generated"))
            else:
                summary = manager.get_summary(
                    ntp_results=ntp_results,
                    url_results=url_results,
                    summary_format=OutputFormat.text,
                )
                self.summary_view.setPlainText(summary)
                self.log_output(self.tr("Text summary generated"))
        except Exception as e:
            msg: str = f"Can't create the summary: {e}"
            self.logger.exception(msg)
            self.show_error(self.tr(f"Can't create the summary {e}"))

    def show_error(self, message: str) -> None:
        """
        Display an error message.

        Display an error message using a QMessageBox and
        logs the error using the logger.

        Args:
        ----
            message: The error message to display.

        """
        self.logger.error(message)
        QMessageBox.critical(self, self.tr("Error"), message)
