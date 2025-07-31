# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
"""
Unit tests for the CheckConnectGUIRunner class.

This module contains comprehensive unit tests to ensure the correct
initialization and functionality of the CheckConnectGUIRunner GUI application.
It uses pytest fixtures for efficient mocking of external dependencies
and PySide6 components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from checkconnect.gui.gui_main import CheckConnectGUIRunner

if TYPE_CHECKING:
    from collections.abc import Iterator

    from PySide6.QtWidgets import QApplication
    from pytest_mock import MockerFixture

    from checkconnect.config.appcontext import AppContext


@pytest.fixture
def gui(q_app: Iterator[QApplication], app_context_fixture: AppContext) -> CheckConnectGUIRunner:
    """
    Create a CheckConnectGUIRunner instance with a mocked context.

    This fixture initializes the GUI application for testing purposes.
    The `q_app` fixture (assumed to be from conftest.py) ensures a QApplication
    instance is available.

    Args:
        q_app (QApplication): The QApplication instance provided by the session-scoped fixture.
        app_context_fixture (AppContext): A mocked application context for dependency injection.

    Returns:
        CheckConnectGUIRunner: An instance of the GUI runner with the GUI shown.
    """
    qapp = q_app.instance  #  noqa: F841
    widget = CheckConnectGUIRunner(context=app_context_fixture)
    widget.show()
    return widget


class TestGuiMain:
    """
    Test suite for the CheckConnectGUIRunner class.

    This class contains individual test methods to verify the behavior of
    various GUI components and their interactions with the backend logic.
    """

    def test_ntp_check_button(
        self,
        mocker: MockerFixture,
        gui: CheckConnectGUIRunner,
    ) -> None:
        """
        Test that the NTP check button triggers the NTP check and logs output.

        Verifies that clicking the NTP button calls the `run_ntp_checks` method
        of the `CheckConnect` instance and that the results are displayed in
        the GUI's output log.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        mock_run_ntp = mocker.patch.object(gui.checkconnect, "run_ntp_checks")
        gui.checkconnect.set_ntp_results(["NTP server 1 OK", "NTP server 2 OK"])

        gui.test_ntp()

        assert "NTP server 1 OK" in gui.output_log.toPlainText()
        assert "NTP server 2 OK" in gui.output_log.toPlainText()
        mock_run_ntp.assert_called_once()

    def test_url_check_button(self, gui: CheckConnectGUIRunner, mocker: MockerFixture) -> None:
        """
        Test that the URL check button triggers the URL check and logs output.

        Verifies that clicking the URL button calls the `run_url_checks` method
        of the `CheckConnect` instance and that the results are displayed in
        the GUI's output log.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        mock_run_url = mocker.patch.object(gui.checkconnect, "run_url_checks")
        gui.checkconnect.set_url_results(["https://example.com OK"])

        gui.test_urls()

        assert "https://example.com OK" in gui.output_log.toPlainText()
        mock_run_url.assert_called_once()

    def test_generate_reports_success(self, gui: CheckConnectGUIRunner, mocker: MockerFixture) -> None:
        """
        Test the successful generation of HTML and PDF reports.

        Mocks the `generate_html_report` and `generate_pdf_report` functions
        to confirm they are called and that a success message is logged in the GUI.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        mock_html = mocker.patch("checkconnect.gui.gui_main.generate_html_report")
        mock_pdf = mocker.patch("checkconnect.gui.gui_main.generate_pdf_report")

        gui.checkconnect.set_ntp_results(["NTP OK"])
        gui.checkconnect.set_url_results(["URL OK"])
        gui.generate_reports()

        mock_html.assert_called_once()
        mock_pdf.assert_called_once()
        assert "Reports generated successfully." in gui.output_log.toPlainText()

    def test_generate_reports_failure(self, gui: CheckConnectGUIRunner, mocker: MockerFixture) -> None:
        """
        Test error handling when report generation fails.

        Mocks the `generate_html_report` to raise an exception, verifying that
        an error message is logged in the GUI's output.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        mocker.patch("checkconnect.gui.gui_main.generate_html_report", side_effect=Exception("Oops"))
        mocker.patch("checkconnect.gui.gui_main.generate_pdf_report")  # Still mock PDF to avoid unpatched call errors

        # Spy on QMessageBox.critical in the same module where show_error lives
        critical_spy = mocker.patch("checkconnect.gui.gui_main.QMessageBox.critical", autospec=True)

        # Also spy on the logger.error call
        log_error_spy = mocker.patch.object(gui.logger, "error")

        # 2) Act
        gui.generate_reports()

        # 3) Assert
        #   a) show_error() called QMessageBox.critical(self, "Error", ...)
        assert critical_spy.call_count == 1
        args, _ = critical_spy.call_args
        # args[0] is the `self` (the gui), args[1] is the translated title "Error"
        # args[2] is the full message
        assert args[1] == gui.tr("Error")
        assert "Failed to generate reports: Oops" in args[2]

        #   b) logger.error was called once with the same message
        log_error_spy.assert_called_once_with(args[2])

    def test_show_summary_html(self, gui: CheckConnectGUIRunner, mocker: MockerFixture) -> None:
        """
        Test the summary view when HTML format is selected.

        Mocks the `ReportManager` and its methods to simulate summary generation
        in HTML format and verifies that the `summary_view` displays HTML content.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        gui.format_selector.setCurrentText("html")
        mock_manager = mocker.patch("checkconnect.gui.gui_main.ReportManager.from_context")
        mock_instance = mock_manager.return_value
        mock_instance.load_previous_results.return_value = (["NTP OK"], ["URL OK"])
        mock_instance.get_summary.return_value = "<h1>Summary</h1>"

        gui.show_summary()

        assert "Summary</span></h1>" in gui.summary_view.toHtml()  # PySide6 might add spans around text

    def test_show_summary_text(self, gui: CheckConnectGUIRunner, mocker: MockerFixture) -> None:
        """
        Test the summary view when plain text format is selected.

        Mocks the `ReportManager` and its methods to simulate summary generation
        in plain text format and verifies that the `summary_view` displays plain text.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        gui.format_selector.setCurrentText("text")
        mock_manager = mocker.patch("checkconnect.gui.gui_main.ReportManager.from_context")
        mock_instance = mock_manager.return_value
        mock_instance.load_previous_results.return_value = (["NTP OK"], ["URL OK"])
        mock_instance.get_summary.return_value = "Summary Text"

        gui.show_summary()

        assert "Summary Text" in gui.summary_view.toPlainText()

    def test_show_summary_exception(self, gui: CheckConnectGUIRunner, mocker: MockerFixture) -> None:
        """
        Test that summary generation errors are logged gracefully.

        Mocks the `ReportManager.from_context` to raise an exception, ensuring
        that an appropriate error message is logged in the GUI's output.

        Args:
            gui (CheckConnectGUIRunner): The GUI instance under test.
            mocker: The pytest-mock fixture for patching objects.
        """
        gui.format_selector.setCurrentText("text")
        mocker.patch("checkconnect.gui.gui_main.ReportManager.from_context", side_effect=Exception("Boom"))

        # Spy on QMessageBox.critical in the same module where show_error lives
        critical_spy = mocker.patch("checkconnect.gui.gui_main.QMessageBox.critical", autospec=True)

        # Also spy on the logger.error call
        log_error_spy = mocker.patch.object(gui.logger, "error")

        # 2) Act
        gui.show_summary()

        # 3) Assert
        #   a) show_error() called QMessageBox.critical(self, "Error", ...)
        assert critical_spy.call_count == 1
        args, _ = critical_spy.call_args
        # args[0] is the `self` (the gui), args[1] is the translated title "Error"
        # args[2] is the full message
        assert args[1] == gui.tr("Error")
        assert "Failed to generate summary: Boom" in args[2]

        #   b) logger.error was called once with the same message
        log_error_spy.assert_called_once_with(args[2])
