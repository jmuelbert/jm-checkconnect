import pytest
from PySide6.QtWidgets import QFileDialog
from PySide6 import QtCore
from checkconnect.gui.checkconnect_gui import CheckConnectGUI

def test_initialization(gui):
    """Test that the GUI initializes correctly."""
    assert gui.ntp_input.text() == ""
    assert gui.url_input.text() == ""
    assert gui.output_log.toPlainText() == ""

def test_browse_ntp_file(gui, monkeypatch):
    """Test the NTP file browsing functionality."""
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: ('/path/to/ntp.csv', ''))
    gui.browse_ntp_file()
    assert gui.ntp_input.text() == '/path/to/ntp.csv'

def test_test_ntp_button(gui, monkeypatch, qtbot):
    """Test the NTP test button functionality."""
    monkeypatch.setattr(gui, 'test_ntp', lambda: gui.output_log.append("NTP test executed."))
    gui.ntp_input.setText('/path/to/ntp.csv')
    qtbot.mouseClick(gui.ntp_button, QtCore.Qt.LeftButton)
    assert gui.output_log.toPlainText().strip() == "NTP test executed."

def test_test_ntp_missing_file(gui, qtbot):
    """Test error handling for missing NTP file."""
    qtbot.mouseClick(gui.ntp_button, QtCore.Qt.LeftButton)
    assert "Invalid or missing NTP file selected." in gui.output_log.toPlainText()

def test_create_reports(gui, monkeypatch, qtbot):
    """Test report generation functionality."""
    monkeypatch.setattr('checkconnect.core.create_reports.create_pdf_report', lambda *args: None)
    monkeypatch.setattr('checkconnect.core.create_reports.create_html_report', lambda *args: None)
    gui.ntp_input.setText('/path/to/ntp.csv')
    gui.url_input.setText('/path/to/url.csv')
    qtbot.mouseClick(gui.report_button, QtCore.Qt.LeftButton)
    assert "Reports generated successfully." in gui.output_log.toPlainText()
