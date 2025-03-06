# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import configparser
import gettext
import os
import unittest
from unittest.mock import MagicMock, patch

from checkconnect.cli.main import CLIMain
from tests.utils import MockLogger


class TestCliMain(unittest.TestCase):
    """
    Unit tests for the CLI main functionality in checkconnect/cli/main.py.

    These tests focus on verifying that the CLIMain class correctly handles both
    successful execution and exceptions during the CLI operations.
    """

    def setUp(self):
        """
        Set up test fixtures before each test method.

        This includes:
        - Creating a config parser with test settings
        - Setting up a mock logger for capturing log output
        - Creating a CLIMain instance with the mock logger
        - Configuring translation handling
        """
        # Create a test configuration
        self.config_parser = configparser.ConfigParser()
        self.config_parser["Files"] = {
            "ntp_servers": "ntp_servers.csv",
            "urls": "urls.csv",
        }
        self.config_parser["Output"] = {"directory": "reports"}
        self.config_parser["Network"] = {"timeout": "5"}
        self.config_parser["Logging"] = {"level": "DEBUG"}

        # Set up logging
        self.mock_logger = MockLogger()

        # Create a CLIMain instance with our mock logger
        self.cli_main = CLIMain()
        self.cli_main.logger = self.mock_logger

        # Set up translations
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "src",
            "checkconnect",
            "cli",
            "locales",
        )

        try:
            self.translate = gettext.translation(
                self.TRANSLATION_DOMAIN,
                self.LOCALES_PATH,
                languages=[os.environ.get("LANG", "en")],
            ).gettext
        except FileNotFoundError:
            # Fallback if translation files aren't found
            self.translate = lambda message: message

    def tearDown(self):
        """Clean up after each test."""
        # Reset the mock logger to ensure clean state for next test
        self.mock_logger.reset()

    def test_cli_main_successful_execution(self):
        """
        Test that CLIMain.run executes successfully.

        This test verifies that when everything works correctly:
        - The CheckConnect class is instantiated with the right parameters
        - The run and generate_reports methods are called
        - Appropriate log messages are generated
        """
        # Create a mock CheckConnect instance
        mock_check_connect = MagicMock()

        # Patch the CheckConnect class to return our mock
        with patch(
            "checkconnect.cli.main.CheckConnect",
            return_value=mock_check_connect,
        ):
            # Run the CLIMain instance
            self.cli_main.run(self.config_parser, "output.txt")

            # Verify expected interactions and log messages
            mock_check_connect.run.assert_called_once()
            mock_check_connect.generate_reports.assert_called_once()

            self.assertIn(
                self.translate("Running CheckConnect in CLI mode"),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate("Reports have been generated."),
                self.mock_logger.infos,
            )

    def test_cli_main_handles_instantiation_exception(self):
        """
        Test that CLIMain.run properly handles exceptions during CheckConnect instantiation.

        This test verifies that when CheckConnect's constructor raises an exception:
        - The exception is caught and not propagated
        - An appropriate error message is logged
        """
        # Create a test exception
        test_exception = Exception("Test initialization error")

        # Patch CheckConnect to raise our test exception when instantiated
        with patch("checkconnect.cli.main.CheckConnect", side_effect=test_exception):
            # Run should not raise an exception
            self.cli_main.run(self.config_parser, "output.txt")

            # Verify the expected log messages
            self.assertIn(
                self.translate("Running CheckConnect in CLI mode"),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate(
                    f"An error occurred during CLI execution: {test_exception}",
                ),
                "".join(self.mock_logger.exceptions),
            )

    def test_cli_main_handles_run_exception(self):
        """
        Test that CLIMain.run properly handles exceptions during the CheckConnect.run method.

        This test verifies that when CheckConnect's run method raises an exception:
        - The exception is caught and not propagated
        - An appropriate error message is logged
        """
        # Create a mock CheckConnect instance that raises an exception when run is called
        mock_check_connect = MagicMock()
        mock_check_connect.run.side_effect = Exception("Test run error")

        # Patch the CheckConnect class to return our mock
        with patch(
            "checkconnect.cli.main.CheckConnect",
            return_value=mock_check_connect,
        ):
            # Run should not raise an exception
            self.cli_main.run(self.config_parser, "output.txt")

            # Verify expected interactions and log messages
            mock_check_connect.run.assert_called_once()
            self.assertFalse(
                mock_check_connect.generate_reports.called,
                "generate_reports should not be called if run fails",
            )

            self.assertIn(
                self.translate("Running CheckConnect in CLI mode"),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate(
                    "An error occurred during CLI execution: Test run error",
                ),
                "".join(self.mock_logger.exceptions),
            )

    def test_cli_main_handles_generate_reports_exception(self):
        """
        Test that CLIMain.run properly handles exceptions during the CheckConnect.generate_reports method.

        This test verifies that when CheckConnect's generate_reports method raises an exception:
        - The exception is caught and not propagated
        - An appropriate error message is logged
        """
        # Create a mock CheckConnect instance that raises an exception when generate_reports is called
        mock_check_connect = MagicMock()
        mock_check_connect.generate_reports.side_effect = Exception(
            "Test report generation error",
        )

        # Patch the CheckConnect class to return our mock
        with patch(
            "checkconnect.cli.main.CheckConnect",
            return_value=mock_check_connect,
        ):
            # Run should not raise an exception
            self.cli_main.run(self.config_parser, "output.txt")

            # Verify expected interactions and log messages
            mock_check_connect.run.assert_called_once()
            mock_check_connect.generate_reports.assert_called_once()

            self.assertIn(
                self.translate("Running CheckConnect in CLI mode"),
                self.mock_logger.infos,
            )
            self.assertIn(
                self.translate(
                    "An error occurred during CLI execution: Test report generation error",
                ),
                "".join(self.mock_logger.exceptions),
            )

    def test_cli_main_wrapper_function(self):
        """
        Test that the cli_main wrapper function correctly creates and uses a CLIMain instance.
        """
        from checkconnect.cli.main import cli_main

        # Patch the CLIMain class
        with patch("checkconnect.cli.main.CLIMain") as mock_cli_main_class:
            # Create a mock instance
            mock_instance = MagicMock()
            mock_cli_main_class.return_value = mock_instance

            # Call the wrapper function
            cli_main(self.config_parser, "output.txt")

            # Verify CLIMain was instantiated and run was called with correct args
            mock_cli_main_class.assert_called_once()
            mock_instance.run.assert_called_once_with(self.config_parser, "output.txt")


if __name__ == "__main__":
    unittest.main()
