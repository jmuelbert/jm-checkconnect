# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import logging
import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from checkconnect.gui.main import gui_main
from tests.utils import MockLogger


class TestGuiMain(unittest.TestCase):
    """Unit tests for gui_main function in checkconnect/gui/main.py."""

    def setUp(self):
        """
        Set up for test methods.

        This includes:
            - Creating a config parser.
            - Creating a MockLogger instance.
        """
        self.config_parser = configparser.ConfigParser()
        self.mock_logger = MockLogger()

        # Translation setup
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "checkconnect",
            "gui",
            "locales",
        )

        try:
            self.translate = gettext.translation(
                self.TRANSLATION_DOMAIN,
                self.LOCALES_PATH,
                languages=[os.environ.get("LANG", "en")],  # Respect the system language
            ).gettext
        except FileNotFoundError:
            # Fallback to the default English translation if the locale is not found
            def translate(message):
                return message

            self.translate = translate

    @patch("checkconnect.gui.main.CheckConnectGUI")
    @patch("checkconnect.gui.main.QApplication")
    @patch("sys.argv", [])  # Mock sys.argv here
    def test_gui_main_success(self, mock_qapplication_class, mock_checkconnect_gui):
        """
        Test successful execution of gui_main.

        This test mocks the CheckConnectGUI and QApplication classes, along with the global logger,
        to simulate a successful execution of the gui_main function. It asserts that the CheckConnectGUI
        class is instantiated with the correct arguments, that the GUI is shown, and that the application
        executes and exits with the expected code.
        """
        # Set up QApplication instance mock
        mock_app_instance = MagicMock()
        # The instance() classmethod should return None first
        # (to indicate no existing QApplication)
        mock_qapplication_class.instance.return_value = None
        # The constructor should return our mock instance
        mock_qapplication_class.return_value = mock_app_instance
        mock_app_instance.exec.return_value = 0  # Return 0 from exec

        # Set up CheckConnectGUI mock
        mock_gui_instance = MagicMock()
        mock_checkconnect_gui.return_value = mock_gui_instance

        # Execute with sys.exit mocked
        with patch("sys.exit") as mock_sys_exit:
            gui_main(self.config_parser, "output.txt", logger=self.mock_logger)

        # Assert logger was used
        self.assertIn("Starting CheckConnect GUI...", self.mock_logger.infos)

        # Assert CheckConnectGUI was created with correct args
        mock_checkconnect_gui.assert_called_once_with(
            self.config_parser,
            "output.txt",
            logger=self.mock_logger,
        )

        # Assert methods were called
        mock_gui_instance.show.assert_called_once()
        mock_app_instance.exec.assert_called_once()
        mock_gui_instance.close.assert_called_once()
        mock_sys_exit.assert_called_once_with(0)
