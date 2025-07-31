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
from checkconnect.reports.report_generator import generate_html_report, generate_pdf_report
from checkconnect.reports.report_manager import OutputFormat, ReportManager

if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext

log = structlog.get_logger(__name__)


class CheckConnectGUIRunner(QWidget):
    """
    Graphical User Interface (GUI) for CheckConnect.

    This class provides the main window and logic for the CheckConnect GUI application.
    It allows users to select NTP and URL files, run connectivity tests, and generate reports.
    It integrates with the `CheckConnect` core logic and `ReportManager` for
    generating and displaying summaries.

    Attributes
    ----------
    context : AppContext
        The application context providing access to shared resources like logger and translator.
    logger : structlog.stdlib.BoundLogger
        The logger instance for logging messages within the GUI.
    translator : Any
        The translator instance for internationalization.
    _ : Callable[[str], str]
        A convenience alias for the translation function.
    config : Any
        The application configuration from the context.
    settings : QSettings
        Qt settings object for persistent application settings.
    language : str | None
        The currently selected language for the GUI.
    checkconnect : CheckConnect
        An instance of the CheckConnect core class for performing network checks.
    ntp_button : QPushButton
        Button to trigger NTP tests.
    url_button : QPushButton
        Button to trigger URL tests.
    report_button : QPushButton
        Button to trigger report generation.
    summary_button : QPushButton
        Button to show a summary of results.
    format_selector : QComboBox
        Dropdown to select the summary output format (text, markdown, html).
    summary_view : QTextBrowser
        Text browser to display the summary.
    output_log : QTextEdit
        Text edit widget to display real-time logs and test results.
    ntp_results : list[str]
        Stores the results of the last NTP check.
    url_results : list[str]
        Stores the results of the last URL check.
    """

    def __init__(
        self,
        context: AppContext,
        language: str | None = None,
    ) -> None:
        """
        Initialize the CheckConnectGUIRunner.

        Initializes the GUI with the provided application context and sets up
        logging, translation, and core `CheckConnect` functionality.

        Args:
        ----
            context (AppContext): Shared application context that includes
                                  logger, translator, and other shared resources.
            language (str | None): Optional language string to set for the GUI.
                                   Defaults to None, which means the system's
                                   locale or a default language will be used.
        """
        super().__init__()

        self.context = context
        self.logger = log
        self.translator = context.translator
        self._ = context.gettext
        self.config = context.settings  # For translations of UI text, if necessary
        self.settings = QSettings("JM", "CheckConnect")
        self.language = language
        self.checkconnect = CheckConnect(context=context)

        # Initialize result lists to avoid AttributeError if tests haven't run yet
        self.ntp_results: list[str] = []
        self.url_results: list[str] = []

        self.setup_gui()

    def tr(self, source_text: str) -> str:
        """
        Implement simple translation method using QApplication's translate.

        Args:
            source_text (str): The text to be translated.

        Returns:
            str: The translated text.
        """
        return QApplication.translate("CheckConnectGUI", source_text)

    def setup_gui(self) -> None:
        """
        Create and configures the GUI layout.

        This method creates all the necessary widgets and layouts for the GUI, including:
            - Buttons to trigger NTP and URL tests, report generation, and application exit.
            - An output log to display real-time test results.
        """
        self.setWindowTitle(
            self.tr("CheckConnect GUI - Version " + __about__.__version__),
        )

        self.resize(800, 600)

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
        QWidget
            A QWidget containing the "Test NTP", "Test URLs", "Generate Report",
            "Show summary", format selector, summary view, and "Exit" buttons.
        """
        button_widget = QWidget()
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
        # Connect both the button and the combobox's selection change to show_summary
        self.format_selector.currentIndexChanged.connect(self.show_summary)
        self.summary_button.clicked.connect(self.show_summary)
        self.summary_view = QTextBrowser()  # This widget will display the summary
        exit_button = QPushButton(self.tr("Exit"))
        exit_button.clicked.connect(self.close)

        # Add widgets to the layout
        layout.addWidget(self.ntp_button)
        layout.addWidget(self.url_button)
        layout.addWidget(self.report_button)
        layout.addWidget(self.summary_button)
        layout.addWidget(self.format_selector)
        # Add summary_view to the main layout if it's meant to be always visible,
        # or handle its visibility and placement as needed.
        # For simplicity, adding it here for now.
        layout.addWidget(self.summary_view)
        layout.addWidget(exit_button)

        return button_widget

    def create_output_log(self) -> QTextEdit:
        """
        Create the QTextEdit widget for displaying output logs.

        Returns
        -------
        QTextEdit
            A QTextEdit widget configured as read-only and with a placeholder text.
            This widget will display test results and logs in real-time.
        """
        self.output_log = QTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setPlaceholderText(self.tr("Results and logs will appear here…"))
        return self.output_log

    def test_ntp(self) -> None:
        """
        Test the NTP servers specified in the configuration.

        Initiates NTP connectivity tests using the `CheckConnect` instance.
        Logs the results of the NTP tests to the output log.
        If an error occurs, it's logged and displayed to the user.
        """
        self.log_output(self.tr("Running NTP tests…"))
        try:
            self.checkconnect.run_ntp_checks()
            ntp_results = self.checkconnect.get_ntp_results()
            for line in ntp_results or []:
                self.log_output(line)
            self.ntp_results = self.checkconnect.get_ntp_results() or []
        except Exception as e:
            self.logger.exception(self._("Error in test_ntp"))
            self.show_error(self.tr(f"NTP test failed: {e}"))
        else:
            self.log_output(self.tr("NTP tests completed."))

    def test_urls(self) -> None:
        """
        Tests the URLs specified in the configuration.

        Initiates URL connectivity tests using the `CheckConnect` instance.
        Logs the results of the URL tests to the output log.
        If an error occurs, it's logged and displayed to the user.
        """
        self.log_output(self.tr("Running URL tests…"))
        try:
            self.checkconnect.run_url_checks()
            url_results = self.checkconnect.get_url_results()
            for line in url_results or []:
                self.log_output(line)
            self.url_results = self.checkconnect.get_url_results() or []
        except Exception as e:
            self.logger.exception(self._("Error in test_urls"))
            self.show_error(self.tr(f"URL test failed: {e}"))
        else:
            self.log_output(self.tr("URL tests completed."))

    def generate_reports(self) -> None:
        """
        Generate HTML and PDF reports from the connectivity test results.

        This method calls the `generate_html_report` and `generate_pdf_report`
        functions. It logs success or displays an error message if report
        generation fails.
        """
        try:
            generate_html_report(
                context=self.context,
                ntp_results=self.checkconnect.get_ntp_results(),
                url_results=self.checkconnect.get_url_results(),
            )

            generate_pdf_report(
                context=self.context,
                ntp_results=self.checkconnect.get_ntp_results(),
                url_results=self.checkconnect.get_url_results(),
            )

        except Exception as e:
            msg = self._(f"Failed to generate reports: {e}")
            self.logger.exception(msg)
            self.show_error(self.tr(f"Failed to generate reports: {e}"))
        else:
            self.log_output(self.tr("Reports generated successfully."))

    def log_output(self, message: str) -> None:
        """
        Appends a message to the GUI's output log and the application logger.

        Args:
        ----
            message (str): The message string to be displayed and logged.
        """
        self.output_log.append(message)
        self.logger.info(message)

    def show_summary(self) -> None:
        """
        Display a formatted summary of connectivity check results in the GUI.

        This method retrieves previous NTP and URL results using `ReportManager`.
        It then generates a summary in the user-selected format (plain text,
        Markdown, or HTML) and displays it in the `summary_view` QTextBrowser.
        If the selected format is HTML, the summary is rendered as rich text;
        otherwise, it is shown as plain text. Errors during the process are
        logged and shown to the user via a message box.

        Raises:
            QMessageBox: Displays a QMessageBox with the error message if any
                         exceptions occur during summary generation.
        """
        try:
            format_text = self.format_selector.currentText()

            report_manager = ReportManager.from_context(self.context)
            summary = report_manager.get_summary(
                summary_format=OutputFormat(format_text),
                ntp_results=self.ntp_results,
                url_results=self.url_results,
            )

            if format_text == "html":
                self.summary_view.setHtml(summary)
                self.log_output(self.tr("HTML summary generated"))
                self.logger.debug(self._("HTML summary generated"))
            else:
                self.summary_view.setPlainText(summary)
                self.log_output(self.tr("Text summary generated"))
                self.logger.debug(self._("Text summary generated"))
        except Exception as e:
            msg: str = self._(f"Can't create the summary: {e}")
            self.logger.exception(msg)
            self.show_error(self.tr(f"Failed to generate summary: {e}"))

    def show_error(self, message: str) -> None:
        """
        Display an error message to the user and logs it.

        Displays an error message using a QMessageBox and logs the error
        using the application's logger.

        Args:
        ----
            message (str): The error message to display.
        """
        self.logger.error(message)
        QMessageBox.critical(self, self.tr("Error"), message)
