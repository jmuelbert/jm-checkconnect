import pytest
from unittest.mock import MagicMock, call, mock_open
from datetime import datetime
from checkconnect.gui.checkconnect_gui import CheckConnectGUI
from PySide6.QtWidgets import QApplication

def test_test_ntp_invalid_file(gui, mocker):
    """Test NTP test with an invalid file."""
    mocker.patch("os.path.exists", return_value=False)
    gui.test_ntp("invalid_file.csv")
    assert "Invalid or missing NTP file selected." in gui.output_log.toPlainText()


def test_test_ntp_success(gui, mocker):
    """Test NTP test with a valid file."""
    mocker.patch("builtins.open", mock_open(read_data="ntp1.example.com\nntp2.example.com\n"))
    mock_request = mocker.patch("ntplib.NTPClient.request")
    mock_request.return_value.tx_time = datetime.now().timestamp()

    gui.test_ntp("ntp_file.csv")

    expected_time = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
    output_text = gui.output_log.toPlainText()

    assert "Running NTP tests..." in output_text
    assert f"NTP: ntp1.example.com - Time: {expected_time}" in output_text
    assert f"NTP: ntp2.example.com - Time: {expected_time}" in output_text


def test_test_urls_invalid_file(gui, mocker):
    """Test URL test with an invalid file."""
    mocker.patch("os.path.exists", return_value=False)
    gui.test_urls("invalid_file.csv")
    assert "Invalid or missing URL file selected." in gui.output_log.toPlainText()


def test_test_urls_success(gui, mocker):
    """Test URL test with a valid file."""
    mocker.patch("builtins.open", mock_open(read_data="http://example.com\nhttps://example.org\n"))
    mock_get = mocker.patch("requests.get", return_value=MagicMock(status_code=200))

    gui.test_urls("url_file.csv")

    output_text = gui.output_log.toPlainText()
    assert "Running URL tests..." in output_text
    assert "URL: http://example.com - Status: 200" in output_text
    assert "URL: https://example.org - Status: 200" in output_text


def test_create_reports(gui, mocker):
    """Test report generation."""
    mocker.patch("fpdf.FPDF.output")
    mocker.patch("builtins.open", mock_open(read_data="ntp1.example.com\nntp2.example.com\n"))
    mocker.patch("builtins.open", mock_open(read_data="http://example.com\nhttps://example.org\n"))
    mock_request = mocker.patch("ntplib.NTPClient.request")
    mock_get = mocker.patch("requests.get", return_value=MagicMock(status_code=200))

    mock_request.return_value.tx_time = datetime.now().timestamp()
    gui.create_reports("ntp_file.csv", "url_file.csv")

    gui.output_log.toPlainText()
    assert "Reports generated successfully." in gui.output_log.toPlainText()
