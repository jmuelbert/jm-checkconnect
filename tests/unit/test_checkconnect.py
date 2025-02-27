import unittest
from unittest.mock import patch

from checkconnect.cli.checkconnect import CheckConnect


class TestCheckConnect(unittest.TestCase):
    """Unit tests for the CheckConnect class."""

    @patch("checkconnect.checkconnect.test_ntp")
    @patch("checkconnect.checkconnect.test_urls")
    def test_run_success(self, mock_test_urls, mock_test_ntp):
        """Test the run method for successful execution of URL and NTP tests."""
        mock_test_ntp.return_value = None
        mock_test_urls.return_value = None

        checkconnect = CheckConnect()
        checkconnect.run()

        mock_test_ntp.assert_called_once()
        mock_test_urls.assert_called_once()

    @patch("checkconnect.checkconnect.test_ntp", side_effect=Exception("NTP Test Error"))
    @patch("checkconnect.checkconnect.test_urls", side_effect=Exception("URL Test Error"))
    def test_run_failure(self, mock_test_urls, mock_test_ntp):
        """Test the run method for handling exceptions during URL and NTP tests."""
        checkconnect = CheckConnect()

        with self.assertRaises(Exception):
            checkconnect.run()

        mock_test_ntp.assert_called_once()
        mock_test_urls.assert_called_once()

    @patch("checkconnect.checkconnect.create_pdf_report")
    @patch("checkconnect.checkconnect.create_html_report")
    def test_generate_reports(self, mock_create_html_report, mock_create_pdf_report):
        """Test the report generation methods."""
        checkconnect = CheckConnect()

        checkconnect.generate_reports()

        mock_create_pdf_report.assert_called_once()
        mock_create_html_report.assert_called_once()


if __name__ == "__main__":
    unittest.main()
