# test_e2e_workflow.py (or your actual test file)

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from PySide6.QtWidgets import QApplication

# Assuming these imports are correct for your project structure
from checkconnect.config.appcontext import AppContext
from checkconnect.core.checkconnect import CheckConnect
from checkconnect.reports.report_generator import (
    ReportGenerator,
    generate_html_report,
    generate_pdf_report,
)
from checkconnect.reports.report_manager import OutputFormat, ReportManager
from checkconnect.gui.gui_main import CheckConnectGUIRunner
import structlog

log = structlog.get_logger(__name__)


@pytest.mark.e2e
def test_cli_workflow(
    tmp_path: Path,
    app_context_fixture: AppContext,  # <--- Changed from dummy_app_context
) -> None:
    """Test complete CLI workflow from initialization to report generation."""
    # Define the desired reports path for this test
    reports_path_for_test = tmp_path / "reports_cli_test"
    data_path_for_test = tmp_path / "data_cli_test"

    # Simulate passing the reports_path as a CLI argument
    # report_manager will get the path from the argument, not from the config initially
    report_generator = ReportGenerator.from_params(app_context_fixture, reports_path_for_test)
    report_manager = ReportManager.from_params(app_context_fixture, data_path_for_test)

    # --- Important Consideration ---
    # As discussed previously, if generate_html_report and generate_pdf_report
    # rely on reading the reports directory directly from `app_context_fixture.settings`,
    # you MUST update the mock settings to reflect the CLI argument.
    # Your `app_context_fixture` provides `context.settings` as a `mocker.Mock()`.
    # You'll need to set up its `get` or `get_section` method to return the `reports_path_for_test`.

    # The mock_app_context fixture already sets a default `test_reports_from_config`
    # for `reports.directory`. To simulate the CLI override, you need to change
    # what the *mocked* `get` method returns.

    # Option 1: Directly modify the mock's side_effect or return_value
    # This ensures that any component calling app_context_fixture.settings.get("reports", "directory")
    # gets the path you want for this specific test case.
    original_get_side_effect = app_context_fixture.settings.get.side_effect

    def cli_test_get_side_effect(section, key, default=None):
        if section == "reports" and key == "directory":
            return str(reports_path_for_test)  # This overrides the config value for this test
        return original_get_side_effect(section, key, default)

    app_context_fixture.settings.get.side_effect = cli_test_get_side_effect

    # Also ensure data_dir is set correctly for tests
    data_dir_for_test = tmp_path / "data_cli_test"
    data_dir_for_test.mkdir(parents=True, exist_ok=True)  # Ensure it exists for the test
    original_data_get_side_effect = app_context_fixture.settings.get.side_effect  # Use the *current* side effect

    def cli_test_get_data_side_effect(section, key, default=None):
        if section == "data" and key == "directory":
            return str(data_dir_for_test)
        return original_data_get_side_effect(section, key, default)

    app_context_fixture.settings.get.side_effect = cli_test_get_data_side_effect

    checker = CheckConnect(context=app_context_fixture)
    checker.run_all_checks()

    generate_html_report(
        context=app_context_fixture,  # This will now read the reports_path_for_test from settings mock
        ntp_results=checker.get_ntp_results(),
        url_results=checker.get_url_results(),
    )

    generate_pdf_report(
        context=app_context_fixture,  # This will now read the reports_path_for_test from settings mock
        ntp_results=checker.get_ntp_results(),
        url_results=checker.get_url_results(),
    )

    # The ReportManager instance itself already has the correct reports_dir
    data_dir_from_manager = report_manager.get_data_dir()  # This will still read from app_context_fixture.settings
    log.info(f"Using data directory for test: {data_dir_from_manager}")

    ntp_results, url_results = report_manager.load_previous_results()
    summary = report_manager.get_summary(
        ntp_results=checker.get_ntp_results(),
        url_results=checker.get_url_results(),
        summary_format=OutputFormat.text,
    )

    # Test the creation of reports
    html_report_path = report_generator.reports_dir / "report.html"
    pdf_report_path = report_generator.reports_dir / "report.pdf"

    assert html_report_path.exists(), "HTML report not found"

    with html_report_path.open("r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    assert soup.title is not None
    assert soup.title.string == "CheckConnect Report"

    assert soup.find("h1", string="CheckConnect Report") is not None
    assert soup.find("h2", string="NTP Results") is not None
    assert soup.find("h2", string="URL Results") is not None

    ntp_results_h2 = soup.find("h2", string="NTP Results")
    assert ntp_results_h2 is not None

    ntp_pre_tag = ntp_results_h2.find_next_sibling("pre")
    assert ntp_pre_tag is not None

    ntp_text = ntp_pre_tag.get_text(strip=True)
    assert "Successfully retrieved time from" in ntp_text

    assert "URL Check Results" in summary
    assert "NTP Check Results" in summary

    assert pdf_report_path.exists(), "PDF report not found"

    assert (Path(data_dir_from_manager) / "ntp_results.json").exists(), "NTP Results JSON file not found"
    assert (Path(data_dir_from_manager) / "url_results.json").exists(), "URL Results JSON file not found"


@pytest.mark.e2e
def test_gui_workflow(
    q_app: QApplication,
    app_context_fixture: AppContext,  # <--- Changed from dummy_app_context
    tmp_path: Path,
) -> None:
    """Test complete GUI workflow including button interactions."""
    reports_path_for_test = tmp_path / "reports_gui_test"
    data_dir_for_test = tmp_path / "data_gui_test"
    data_dir_for_test.mkdir(parents=True, exist_ok=True)  # Ensure it exists for the test

    # For GUI tests, you're simulating the app starting up and then GUI actions.
    # The AppContext's settings should reflect the *initial* state or any config file override.
    # If the GUI *itself* has an option to override paths, you'd mock that interaction.
    # For this test, let's just make sure the mocked settings return the desired paths.

    # Modify the mock's get method for this test's specific paths
    original_get_side_effect = app_context_fixture.settings.get.side_effect

    def gui_test_get_side_effect(section, key, default=None):
        if section == "reports" and key == "directory":
            return str(reports_path_for_test)
        if section == "data" and key == "directory":
            return str(data_dir_for_test)
        return original_get_side_effect(section, key, default)

    app_context_fixture.settings.get.side_effect = gui_test_get_side_effect

    # Assuming CheckConnectGUIRunner's internal ReportManager creation respects AppContext
    gui = CheckConnectGUIRunner(context=app_context_fixture, language="de")

    # The ReportManager created by the GUI (or explicitly here for testing its path logic)
    # This simulates the GUI perhaps calling ReportManager.from_context (no CLI arg)
    # which would then pull the `reports_path_for_test` from the now-modified `app_context_fixture.settings`.
    manager = ReportManager.from_context(context=app_context_fixture)  # Simulating GUI internal logic

    generator = ReportGenerator.from_context(context=app_context_fixture)

    data_dir_from_manager = manager.get_data_dir()
    log.info(f"Using data directory for GUI test: {data_dir_from_manager}")

    gui.test_ntp()
    gui.test_urls()
    gui.generate_reports()  # This action should use the reports_path_for_test
    gui.show_summary()

    log_text = gui.output_log.toPlainText()

    assert "NTP" in log_text, "NTP test not found in log"
    assert "Status: 200" in log_text, "URL test not found in log"
    assert "Reports generated successfully" in log_text, "Reports generated successfully not found in log"
    print("----")
    print(log_text)
    print("----")

    assert "summary generated" in log_text, "summary generated not found in log"

    # Use manager.reports_dir for asserts (it reflects what the ReportGenerator itself calculated)
    assert (generator.reports_dir / "report.html").exists(), "HTML report not found"
    assert (generator.reports_dir / "report.pdf").exists(), "PDF report not found"

    assert (Path(data_dir_from_manager) / "ntp_results.json").exists(), "NTP Results JSON file not found"
    assert (Path(data_dir_from_manager) / "url_results.json").exists(), "URL Results JSON file not found"
