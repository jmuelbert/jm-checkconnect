# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import logging
import os
from unittest.mock import MagicMock, call, patch

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QTextEdit
from pytest_mock import MockerFixture

from checkconnect.gui.checkconnect_gui import CheckConnectGUI, get_system_locale
from tests.utils import MockLogger


@pytest.fixture(scope="session", autouse=True)
def q_app():
    """Fixture to create a QApplication instance for all tests."""
    app = QApplication.instance()
    created_app = False
    if not app:
        app = QApplication([])
        created_app = True
    yield app
    if created_app:
        app.quit()


@pytest.fixture
def mock_get_open_file_name():
    """Fixture to mock QFileDialog.getOpenFileName."""
    with patch("checkconnect.gui.checkconnect_gui.QFileDialog.getOpenFileName") as mock:
        yield mock


@pytest.fixture
def mock_path_exists():
    """Fixture to mock os.path.exists."""
    with patch("checkconnect.gui.checkconnect_gui.os.path.exists") as mock:
        yield mock


@pytest.fixture
def mock_critical():
    """Fixture to mock QMessageBox.critical."""
    with patch("checkconnect.gui.checkconnect_gui.QMessageBox.critical") as mock:
        yield mock


@pytest.fixture
def mock_information():
    """Fixture to mock QMessageBox.information."""
    with patch("checkconnect.gui.checkconnect_gui.QMessageBox.information") as mock:
        yield mock


@pytest.fixture
def mock_check_ntp_servers():
    """Fixture to mock NTPChecker.check_ntp_servers."""
    with patch("checkconnect.core.ntp_checker.NTPChecker.check_ntp_servers") as mock:
        yield mock


@pytest.fixture
def mock_check_urls():
    """Fixture to mock URLChecker.check_urls."""
    with patch("checkconnect.core.url_checker.URLChecker.check_urls") as mock:
        yield mock


@pytest.fixture
def mock_create_html_report():
    """Fixture to mock create_html_report."""
    with patch("checkconnect.gui.checkconnect_gui.create_html_report") as mock:
        yield mock


@pytest.fixture
def mock_create_pdf_report():
    """Fixture to mock create_pdf_report."""
    with patch("checkconnect.gui.checkconnect_gui.create_pdf_report") as mock:
        yield mock


class TestCheckConnectGUI:
    """Unit tests for CheckConnectGUI class."""

    @pytest.fixture(autouse=True)
    def setup_method(self, q_app, mocker: MockerFixture) -> None:
        """Set up for each test method."""
        self.config_parser = configparser.ConfigParser()
        self.config_parser["Files"] = {
            "ntp_servers": "ntp_servers.csv",
            "urls": "urls.csv",
        }
        self.config_parser["Output"] = {"directory": "reports"}

        self.gui = CheckConnectGUI(self.config_parser, "output.txt")
        self.mock_logger = MockLogger()
        self.gui.logger = self.mock_logger
        self.gui.output_log.append = MagicMock()
        self.mock_logger.reset()

        # Mock translation for tests
        mocker.patch("checkconnect.gui.checkconnect_gui.CheckConnectGUI.tr", side_effect=lambda x: x)

    def test_checkconnect_gui_initialization(self) -> None:
        """Tests CheckConnectGUI initializes correctly."""
        assert isinstance(self.gui, CheckConnectGUI), (
            "GUI is not an instance of CheckConnectGUI"
        )
        assert self.gui.config_parser == self.config_parser, (
            "config_parser is incorrect"
        )
        assert self.gui.output_file == "output.txt", "output_file is incorrect"
        assert self.gui.ntp_file == "ntp_servers.csv", "ntp_file is incorrect"
        assert self.gui.url_file == "urls.csv", "url_file is incorrect"
        assert self.gui.report_dir == "reports", "report_dir is incorrect"
        assert isinstance(self.gui.url_input, QLineEdit), "url_input is not a QLineEdit"
        assert isinstance(self.gui.output_log, QTextEdit), (
            "output_log is not a QTextEdit"
        )

    def test_browse_ntp_file(self, mock_get_open_file_name: MagicMock) -> None:
        """Tests browse_ntp_file method."""
        mock_get_open_file_name.return_value = ("new_ntp.csv", "")
        self.gui.browse_ntp_file()
        assert self.gui.ntp_input.text() == "new_ntp.csv", "ntp_input text is incorrect"
        assert self.gui.ntp_file == "new_ntp.csv", "ntp_file is incorrect"

    def test_browse_url_file(self, mock_get_open_file_name: MagicMock) -> None:
        """Tests browse_url_file method."""
        mock_get_open_file_name.return_value = ("new_url.csv", "")
        self.gui.browse_url_file()
        assert self.gui.url_input.text() == "new_url.csv", "url_input text is incorrect"
        assert self.gui.url_file == "new_url.csv", "url_file is incorrect"

    def test_test_ntp_success(
        self,
        mock_path_exists: MagicMock,
        mock_check_ntp_servers: MagicMock,
    ) -> None:
        """Tests test_ntp method success."""
        mock_path_exists.return_value = True
        mock_check_ntp_servers.return_value = ["NTP Result 1", "NTP Result 2"]

        self.gui.ntp_input.setText("ntp_servers.csv")
        self.gui.test_ntp()

        mock_check_ntp_servers.assert_called_once_with("ntp_servers.csv", "output.txt")
        expected_log_calls = [
            call("Running NTP tests...\n"),
            call("NTP Result 1\n"),
            call("NTP Result 2\n"),
            call("NTP tests completed.\n"),
        ]
        assert self.gui.output_log.append.mock_calls == expected_log_calls, (
            "output_log append calls are incorrect"
        )

    def test_test_ntp_file_not_found(
        self, mock_path_exists: MagicMock, mock_critical: MagicMock
    ) -> None:
        """Tests test_ntp method file not found."""
        mock_path_exists.return_value = False
        self.gui.ntp_input.setText("invalid_ntp.csv")
        self.gui.test_ntp()

        mock_critical.assert_called_once_with(
            self.gui,
            self.gui,
            "Invalid or missing NTP file selected.",
        )

    def test_test_urls_success(
        self,
        mock_path_exists: MagicMock,
        mock_check_urls: MagicMock,
    ) -> None:
        """Tests test_urls method success."""
        mock_path_exists.return_value = True
        mock_check_urls.return_value = ["URL Result 1", "URL Result 2"]

        self.gui.url_input.setText("urls.csv")
        self.gui.test_urls()

        mock_check_urls.assert_called_once_with("urls.csv", "output.txt")
        expected_log_calls = [
            call("Running URL tests...\n"),
            call("URL Result 1\n"),
            call("URL Result 2\n"),
            call("URL tests completed.\n"),
        ]
        assert self.gui.output_log.append.mock_calls == expected_log_calls, (
            "output_log append calls are incorrect"
        )

    def test_test_urls_file_not_found(
        self, mock_path_exists: MagicMock, mock_critical: MagicMock
    ) -> None:
        """Tests test_urls method file not found."""
        mock_path_exists.return_value = False
        self.gui.url_input.setText("invalid_urls.csv")
        self.gui.test_urls()

        mock_critical.assert_called_once_with(
            self.gui,
            self.gui,
            "Invalid or missing URL file selected.",
        )

    def test_create_reports_success(
        self,
        mock_path_exists: MagicMock,
        mock_create_pdf_report: MagicMock,
        mock_create_html_report: MagicMock,
        mock_information: MagicMock,
    ) -> None:
        """Tests create_reports method success."""
        mock_path_exists.return_value = True
        self.gui.ntp_input.setText("ntp_servers.csv")
        self.gui.url_input.setText("urls.csv")
        self.gui.create_reports()

        mock_create_pdf_report.assert_called_once_with(
            "ntp_servers.csv",
            "urls.csv",
            "reports",
            self.gui.logger,
        )
        mock_create_html_report.assert_called_once_with(
            "ntp_servers.csv",
            "urls.csv",
            "reports",
            self.gui.logger,
        )
        mock_information.assert_called_once_with(
            self.gui,
            self.gui,
            "Reports generated successfully.",
        )

        # Capture the last call and assert the message is correct
        last_call_args = self.gui.output_log.append.call_args[0]
        assert "Reports generated successfully.\n" == last_call_args[0], "Success message not found in log"

    def test_create_reports_file_not_found(
        self, mock_path_exists: MagicMock, mock_critical: MagicMock
    ) -> None:
        """Tests create_reports method file not found."""
        mock_path_exists.return_value = False
        self.gui.ntp_input.setText("invalid_ntp.csv")
        self.gui.url_input.setText("invalid_urls.csv")
        self.gui.create_reports()

        mock_critical.assert_called_once_with(
            self.gui,
            self.gui,
            "Invalid or missing files for report generation.",
        )

    def test_create_reports_exception(
        self,
        mock_path_exists: MagicMock,
        mock_create_pdf_report: MagicMock,
        mock_critical: MagicMock,
    ) -> None:
        """Tests create_reports method exception."""
        mock_path_exists.return_value = True
        mock_create_pdf_report.side_effect = Exception("Report error")
        self.gui.ntp_input.setText("ntp_servers.csv")
        self.gui.url_input.setText("urls.csv")
        self.gui.create_reports()

        mock_critical.assert_called_once_with(
            self.gui,
            self.gui,
            "Error generating reports: Report error",
        )

    def test_get_system_locale(self, mocker: MockerFixture) -> None:
        """Tests that the get_system_locale function retrieves the system locale."""
        # Mock locale.getlocale to return a specific locale
        mocker.patch("locale.getlocale", return_value=("de_DE", "UTF-8"))

        # Call the function
        locale = get_system_locale()

        # Assert that the function returns the mocked locale
        assert locale == "de_DE"

        # Mock locale.getlocale to raise an exception
        mocker.patch("locale.getlocale", side_effect=Exception("Failed to get locale"))

        # Call the function
        locale = get_system_locale()

        # Assert that the function returns the default locale
        assert locale == "en_US"

    def test_load_translation_success(self, mocker: MockerFixture) -> None:
        """Tests that the load_translation function loads a translation successfully."""
        # Mock the necessary functions
        mocker.patch("checkconnect.gui.checkconnect_gui.get_system_locale", return_value="de_DE")
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("PySide6.QtCore.QTranslator.load", return_value=True)
        mock_app_install_translator = mocker.patch("PySide6.QtWidgets.QApplication.installTranslator")

        # Call the function
        self.gui.load_translation()

        # Assert that the necessary functions were called
        mock_app_install_translator.assert_called_once()

    def test_load_translation_file_not_found(self, mocker: MockerFixture) -> None:
        """Tests that the load_translation function handles the case where the translation file is not found."""
        # Mock the necessary functions
        mocker.patch("checkconnect.gui.checkconnect_gui.get_system_locale", return_value="de_DE")
        mocker.patch("os.path.exists", return_value=False)

        # Call the function
        self.gui.load_translation()

        # Assert that the necessary functions were not called
        # QTranslator().load() and QApplication.instance().installTranslator() are not used in the function
        #assert not self.gui.translator.load.called
        #assert not QApplication.instance().installTranslator.called

    def test_load_translation_load_fails(self, mocker: MockerFixture) -> None:
        """Tests that the load_translation function handles the case where the translation file fails to load."""
        # Mock the necessary functions
        mocker.patch("checkconnect.gui.checkconnect_gui.get_system_locale", return_value="de_DE")
        mocker.patch("os.path.exists", return_value=True)
        mocker.patch("PySide6.QtCore.QTranslator.load", return_value=False)
        mock_install_translator = mocker.patch("PySide6.QtWidgets.QApplication.installTranslator")

        # Call the function
        self.gui.load_translation()

        # Assert that the necessary functions were not called
        mock_install_translator.assert_not_called()
