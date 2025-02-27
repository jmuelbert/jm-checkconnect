import unittest
from unittest.mock import mock_open, patch, MagicMock
from checkconnect.core.create_reports import create_html_report, create_pdf_report

class TestCreateReports(unittest.TestCase):
    """Unit tests for the report creation functionality."""

    @patch("checkconnect.core.create_reports.FPDF")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_pdf_report(self, mock_open, MockFPDF):
        """
        Test the creation of a PDF report.
        This test mocks the FPDF class and verifies that the PDF report is generated correctly.
        """
        # Create a mock PDF object
        mock_pdf = MockFPDF.return_value

        # Mock the content of the NTP and URL files
        mock_open.side_effect = [
            mock_open(read_data="europe.pool.ntp.org\ngoogle.ntp.com").return_value,
            mock_open(read_data="http://example.com\nhttp://another-example.com").return_value
        ]

        # Call the function to create the PDF report
        create_pdf_report("mock_ntp_file.txt", "mock_url_file.txt")

        # Assert that the add_page method was called once
        mock_pdf.add_page.assert_called_once()
        # Assert that the output method was called with the correct filename
        mock_pdf.output.assert_called_once_with("connectivity_report.pdf")

        # Assert that the correct methods were called for NTP and URL processing
        self.assertGreater(mock_pdf.cell.call_count, 0)  # Ensure cell was called at least once

    @patch("builtins.open", new_callable=mock_open)
    def test_create_html_report(self, mock_file):
        """
        Test the creation of an HTML report.
        This test verifies that the HTML report is generated correctly and written to a file.
        """
        # Create mock file handles for NTP and URL files
        mock_ntp_file = mock_open(read_data="europe.pool.ntp.org\ngoogle.ntp.com").return_value
        mock_url_file = mock_open(read_data="http://example.com\nhttp://another-example.com").return_value

        # Set the side effect to return the mock file handles
        mock_file.side_effect = [mock_ntp_file, mock_url_file]

        # Call the function to create the HTML report
        create_html_report("mock_ntp_file.txt", "mock_url_file.txt")

        # Assert that the output file was opened in write mode
        mock_file.assert_any_call("connectivity_report.html", "w")
        # Assert that the write method was called on the output file
        mock_file().write.assert_any_call("<html><head><title>Connectivity Report</title></head>")
        mock_file().write.assert_any_call("</body></html>")

        # Ensure that the HTML content includes the expected elements
        self.assertIn("<h1>Connectivity Report</h1>", mock_file().write.call_args_list[0][0][0])
        self.assertIn("<h2>NTP-Test:</h2>", mock_file().write.call_args_list[1][0][0])
        self.assertIn("<h2>URL-Test:</h2>", mock_file().write.call_args_list[2][0][0])

if __name__ == "__main__":
    unittest.main()
