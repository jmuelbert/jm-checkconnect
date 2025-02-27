import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from checkconnect.gui.checkconnect_gui import CheckConnectGUI


@pytest.fixture(scope="session", autouse=True)
def app():
    """Ensure QApplication is initialized for GUI tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.quit()


@pytest.fixture
def gui(qtbot, app):
    """Fixture to create and return a CheckConnectGUI instance."""
    window = CheckConnectGUI()
    qtbot.addWidget(window)
    return window


# Mocking NTP Client requests
@pytest.fixture
def mock_ntp_request():
    """Mock NTPClient request globally."""
    with patch("checkconnect.core.ntp_checker.ntplib.NTPClient.request") as mock:
        yield mock


# Mocking HTTP GET requests
@pytest.fixture
def mock_http_get():
    """Mock HTTP GET requests globally."""
    with patch("checkconnect.core.url_checker.requests.get") as mock:
        yield mock


# File Fixtures
@pytest.fixture
def ntp_file(tmp_path):
    """Create a temporary NTP test file."""
    ntp_test_file = tmp_path / "mock_ntp_file.txt"
    ntp_test_file.write_text("NTP data")
    return str(ntp_test_file)


@pytest.fixture
def url_file(tmp_path):
    """Create a temporary URL test file."""
    url_test_file = tmp_path / "mock_url_file.txt"
    url_test_file.write_text("URL data")
    return str(url_test_file)


@pytest.fixture
def output_file(tmp_path):
    """Create a temporary output file."""
    output_file_path = tmp_path / "mock_output_file.txt"
    return str(output_file_path)


# Mocking PDF and HTML Report Generation
@pytest.fixture
def mock_pdf():
    """Mock PDF report generation."""
    with patch("checkconnect.core.create_reports.FPDF") as mock:
        yield mock


@pytest.fixture
def mock_html():
    """Mock HTML report generation."""
    with patch("checkconnect.core.create_reports.create_html_report") as mock:
        yield mock
