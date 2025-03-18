import pytest
from unittest.mock import MagicMock
from checkconnect.gui.checkconnect_gui import CheckConnectGUI
import configparser
import os
from PySide6.QtWidgets import QMessageBox

@pytest.fixture
def config_parser():
    config = configparser.ConfigParser()
    config.read_dict({
        'Output': {'directory': 'test_reports'},
        'Files': {'ntp_servers': 'test_ntp.csv', 'urls': 'test_urls.csv'}
    })
    return config

@pytest.fixture
def gui(qtbot, config_parser):
    gui = CheckConnectGUI(config_parser)
    qtbot.addWidget(gui)
    return gui

def test_load_translation(gui, mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch.object(gui.translator, 'load', return_value=True)
    app = MagicMock()
    mocker.patch('PySide6.QtWidgets.QApplication.instance', return_value=app)

    gui.load_translation()

    app.installTranslator.assert_called_once_with(gui.translator)
    gui.logger.info.assert_called_once_with("Translation loaded for locale: en_US")

def test_browse_ntp_file(gui, mocker):
    mocker.patch('PySide6.QtWidgets.QFileDialog.getOpenFileName', return_value=('test_ntp.csv', ''))
    gui.browse_ntp_file()
    assert gui.ntp_input.text() == 'test_ntp.csv'
    assert gui.ntp_file == 'test_ntp.csv'

def test_browse_url_file(gui, mocker):
    mocker.patch('PySide6.QtWidgets.QFileDialog.getOpenFileName', return_value=('test_urls.csv', ''))
    gui.browse_url_file()
    assert gui.url_input.text() == 'test_urls.csv'
    assert gui.url_file == 'test_urls.csv'

def test_test_ntp(gui, mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch.object(gui.ntp_checker, 'check_ntp_servers', return_value=['NTP test result'])

    gui.ntp_input.setText('test_ntp.csv')
    gui.test_ntp()

    assert 'Running NTP tests...\n' in gui.output_log.toPlainText()
    assert 'NTP test result\n' in gui.output_log.toPlainText()
    assert 'NTP tests completed.\n' in gui.output_log.toPlainText()

def test_test_urls(gui, mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch.object(gui.url_checker, 'check_urls', return_value=['URL test result'])

    gui.url_input.setText('test_urls.csv')
    gui.test_urls()

    assert 'Running URL tests...\n' in gui.output_log.toPlainText()
    assert 'URL test result\n' in gui.output_log.toPlainText()
    assert 'URL tests completed.\n' in gui.output_log.toPlainText()

def test_create_reports(gui, mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('checkconnect.core.create_reports.create_pdf_report')
    mocker.patch('checkconnect.core.create_reports.create_html_report')

    gui.ntp_input.setText('test_ntp.csv')
    gui.url_input.setText('test_urls.csv')
    gui.create_reports()

    assert 'Reports generated successfully.\n' in gui.output_log.toPlainText()
    gui.logger.info.assert_called_once_with("Reports generated successfully.")

def test_create_reports_with_error(gui, mocker):
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('checkconnect.core.create_reports.create_pdf_report', side_effect=Exception('PDF error'))
    mocker.patch('checkconnect.core.create_reports.create_html_report', side_effect=Exception('HTML error'))

    gui.ntp_input.setText('test_ntp.csv')
    gui.url_input.setText('test_urls.csv')
    with mocker.patch('PySide6.QtWidgets.QMessageBox.critical') as mock_critical:
        gui.create_reports()
        mock_critical.assert_called_once_with(
            gui,
            gui.tr("Error"),
            gui.tr("Error generating reports: HTML error")
        )
        gui.logger.exception.assert_called_once_with("Error generating reports.")
