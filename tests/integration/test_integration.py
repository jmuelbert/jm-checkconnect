# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import gettext
import os
import shutil
import subprocess
import sys
import unittest
from configparser import RawConfigParser
from io import StringIO
from unittest.mock import patch


class TestIntegration(unittest.TestCase):
    """
    Integration tests for CheckConnect CLI.

    These tests verify the end-to-end functionality of the CheckConnect CLI
    using both subprocess calls and direct imports to test the application.
    """

    def setUp(self):
        """
        Set up test environment.

        This method creates a temporary directory and populates it with the
        necessary configuration and data files for the integration tests.
        """
        # Create test directory structure
        self.test_dir = "integration_test_dir"
        os.makedirs(self.test_dir, exist_ok=True)

        # Create config.ini file
        self.config_file = os.path.join(self.test_dir, "config.ini")
        config = configparser.RawConfigParser()
        config["Logging"] = {
            "level": "DEBUG",
            "console_handler_level": "DEBUG",
            "file_handler_level": "DEBUG",
            "file_handler_file": os.path.join(self.test_dir, "checkconnect.log"),
            # IMPORTANT: Double the percent signs to escape them in the config file
            "simple_formatter_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }

        config["Output"] = {"directory": os.path.join(self.test_dir, "test_reports")}
        config["Files"] = {
            "ntp_servers": os.path.join(self.test_dir, "ntp_servers.txt"),
            "urls": os.path.join(self.test_dir, "urls.txt"),
        }
        config["Network"] = {"timeout": "2"}

        with open(self.config_file, "w") as f:
            config.write(f)

        # Create NTP and URL files with test data
        self.ntp_file = os.path.join(self.test_dir, "ntp_servers.txt")
        with open(self.ntp_file, "w") as f:
            f.write("pool.ntp.org\n")

        self.url_file = os.path.join(self.test_dir, "urls.txt")
        with open(self.url_file, "w") as f:
            f.write("https://www.example.com\n")

        # Define directory for reports
        self.reports_dir = os.path.join(self.test_dir, "test_reports")
        os.makedirs(self.reports_dir, exist_ok=True)

        # Define log file path
        self.log_file = os.path.join(self.test_dir, "checkconnect.log")

        # Setup translations
        self.TRANSLATION_DOMAIN = "checkconnect"
        self.LOCALES_PATH = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'src', 'checkconnect', 'locales',
        )

        try:
            self.translate = gettext.translation(
                self.TRANSLATION_DOMAIN,
                self.LOCALES_PATH,
                languages=[os.environ.get('LANG', 'en')],
            ).gettext
        except FileNotFoundError:
            # Fallback to a simple identity function
            self.translate = lambda message: message

    def tearDown(self):
        """
        Clean up test environment.

        This method removes the temporary test directory and all its contents.
        """
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_report_generation(self):
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        test_script = os.path.join(self.test_dir, "test_script.py")

        with open(test_script, 'w') as f:
            f.write("""
import configparser
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from checkconnect.core.create_reports import create_html_report, create_pdf_report

def main():
    config_file = sys.argv[1]

    # Parse config
    config = configparser.ConfigParser()
    config.read(config_file)

    # Get file paths
    ntp_file = config.get("Files", "ntp_servers")
    url_file = config.get("Files", "urls")
    output_dir = config.get("Output", "directory")

    # Generate reports
    print(f"Generating reports with files: {ntp_file}, {url_file}, output dir: {output_dir}")
    create_html_report(ntp_file, url_file, output_dir)
    create_pdf_report(ntp_file, url_file, output_dir)
    print("Reports generated successfully")

if __name__ == "__main__":
    main()
""")

        # Run the script
        command = ["python", test_script, self.config_file]

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)

            print(f"Report script output: {result.stdout}")
            print(f"Report script errors: {result.stderr}")

            # Check that the script executed successfully
            self.assertEqual(result.returncode, 0, f"Report script failed: {result.stderr}")

            # Check that report files were created
            html_report = os.path.join(self.reports_dir, "report.html")
            pdf_report = os.path.join(self.reports_dir, "report.pdf")

            # Debug directory contents
            print(f"Reports directory: {self.reports_dir}")
            if os.path.exists(self.reports_dir):
                print(f"Reports directory contents: {os.listdir(self.reports_dir)}")

            # Verify reports exist
            self.assertTrue(os.path.exists(html_report), f"HTML report not found at {html_report}")
            self.assertTrue(os.path.exists(pdf_report), f"PDF report not found at {pdf_report}")

            # Check HTML report content
            with open(html_report) as f:
                html_content = f.read()
                self.assertIn("CheckConnect Report", html_content)
                self.assertIn("NTP Results", html_content)
                self.assertIn("URL Results", html_content)

        except Exception as e:
            print(f"Exception during report generation test: {e}")
            raise

    def test_subprocess_execution(self):
        """
        Test the application using subprocess to run the actual CLI command.

        This test verifies command-line execution and checks log file output.
        """
        # Construct the command to run
        command = [
            "python", "-m", "checkconnect",
            "-c", self.config_file,
            "-v",  # Verbose mode
        ]

        # Print debugging information
        print(f"Working directory: {os.getcwd()}")
        print(f"Command: {' '.join(command)}")
        print(f"Config file: {self.config_file}")
        print(f"Config file exists: {os.path.exists(self.config_file)}")

        # Create a test environment with PYTHONPATH set to find the module
        test_env = os.environ.copy()
        test_env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # Run the command
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                env=test_env,
            )

            # Print execution results for debugging
            print(f"Command exit code: {result.returncode}")
            print(f"Command stdout: {result.stdout}")
            print(f"Command stderr: {result.stderr}")

            # Check that the command executed successfully
            self.assertEqual(result.returncode, 0, f"Command failed with code {result.returncode}: {result.stderr}")

            # Check that log file was created
            self.assertTrue(os.path.exists(self.log_file), f"Log file not created at {self.log_file}")

            # Read log file and check for expected output
            with open(self.log_file) as f:
                log_content = f.read()
                print(f"Log file content: {log_content}")

            # Check for expected messages in combined output and log file
            combined_output = result.stdout + result.stderr + log_content
            self.assertIn("Starting CheckConnect", combined_output)

        except Exception as e:
            print(f"Exception during subprocess test: {e}")
            raise


if __name__ == "__main__":
    unittest.main()
