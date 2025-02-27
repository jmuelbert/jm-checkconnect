import pytest
from unittest.mock import MagicMock
from checkconnect.cli.checkconnect import CheckConnect


@pytest.fixture
def checkconnect(output_file):
    """Fixture to initialize CheckConnect instance."""
    return CheckConnect(output_file=output_file)


def test_integration(checkconnect, mock_ntp_request, mock_http_get, ntp_file, url_file, output_file):
    """
    Test the integration of CheckConnect:
    - Simulates NTP & URL responses
    - Verifies report generation
    """
    # Simulate successful NTP response
    mock_ntp_response = MagicMock()
    mock_ntp_response.tx_time = 1629393939  # Mocked timestamp
    mock_ntp_request.return_value = mock_ntp_response

    # Simulate successful URL response
    mock_http_get.return_value.status_code = 200

    # Run the test
    checkconnect.run()

    # Verify calls
    mock_ntp_request.assert_called()
    mock_http_get.assert_called()

    # Verify the output file contents
    with open(output_file) as f:
        content = f.read()
        print(f"DEBUG: File Content:\n{content}")  # Debugging output
        assert "NTP-Test:" in content, f"Expected 'NTP-Test:' but got: {content}"
        assert "URL-Test:" in content, f"Expected 'URL-Test:' but got: {content}"

    # Generate reports
    checkconnect.generate_reports()

    # Verify that reports were created
    mock_pdf.assert_called_once()
    mock_html.assert_called_once()
    print(f"DEBUG: PDF Report generated at {pdf_report_path}")
    print(f"DEBUG: HTML Report generated at {html_report_path}")
