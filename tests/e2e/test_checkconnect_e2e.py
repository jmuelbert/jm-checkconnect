# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from PySide6.QtWidgets import QApplication

from checkconnect.config.appcontext import AppContext
from checkconnect.core.checkconnect import CheckConnect
from checkconnect.reports.report_generator import (
    generate_html_report,
    generate_pdf_report,
)
from checkconnect.reports.report_manager import OutputFormat, ReportManager


@pytest.mark.e2e
def test_cli_workflow(tmp_path: Path, dummy_app_context: AppContext) -> None:
    """Test complete CLI workflow from initialization to report generation."""
    # Initialize components using overridden config

    # context = initialize_app_context(config_file=Path(tmp_path / "config.toml"), language="de")
    # Run all checks
    # Generate two lists:
    # 1. ntp results
    # 2. url results
    checker = CheckConnect(context=dummy_app_context)
    reports_path = tmp_path / "reports"
    html_report_path = reports_path / "report.html"
    pdf_report_path = reports_path / "report.pdf"

    checker.config.set("reports", "directory", str(reports_path))
    checker.run_all_checks()

    # Generate reports for the results found by checker.
    generate_html_report(
        context=dummy_app_context,
        ntp_results=checker.ntp_results,
        url_results=checker.url_results,
    )

    generate_pdf_report(
        context=dummy_app_context,
        ntp_results=checker.ntp_results,
        url_results=checker.url_results,
    )

    # Generate summary from saved json-results by checker.
    manager = ReportManager.from_context(context=dummy_app_context)
    manager.context.config.set("data", "directory", str(tmp_path))
    data_dir = manager.get_data_dir()
    print(data_dir)

    ntp_results, url_results = manager.load_previous_results()
    summary = manager.get_summary(
        ntp_results=ntp_results,
        url_results=url_results,
        summary_format=OutputFormat.text,
    )

    # Test the creation of reports
    if not html_report_path.exists():
        raise AssertionError("HTML report not found")

    with html_report_path.open("r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Prüfen des <title>-Tags
    assert soup.title is not None
    assert soup.title.string == "CheckConnect Report"

    # Prüfen der Hauptüberschrift <h1>
    assert soup.find("h1", string="CheckConnect Report") is not None

    # Prüfen der Unterüberschriften <h2>
    assert soup.find("h2", string="NTP Results") is not None
    assert soup.find("h2", string="URL Results") is not None

    # Finden Sie den <pre>-Block nach der "NTP Results"-Überschrift
    ntp_results_h2 = soup.find("h2", string="NTP Results")
    assert ntp_results_h2 is not None

    # Nehmen Sie an, der nächste <pre>-Tag nach der h2-Überschrift enthält die NTP-Ergebnisse
    ntp_pre_tag = ntp_results_h2.find_next_sibling("pre")
    assert ntp_pre_tag is not None

    # Überprüfen Sie den Textinhalt
    ntp_text = ntp_pre_tag.get_text(strip=True)  # strip=True entfernt führende/nachfolgende Leerzeichen
    assert "NTP: pool.ntp.org - Time:" in ntp_text

    # Sie könnten hier auch eine exakte Übereinstimmung mit dem gesamten Block prüfen,
    # wenn der Inhalt immer identisch sein sollte:
    # expected_ntp_text = "NTP Server 1: OK\nNTP Server 2: FAILED"
    # assert ntp_text == expected_ntp_text
    # Für PDF ist es schwieriger, aber hier ein Ansatz:
    # from pypdf import PdfReader # oder eine andere PDF-Bibliothek
    # pdf_report_path = Path(reports_path) / "report.pdf"
    # assert pdf_report_path.exists(), "PDF report not found"
    # reader = PdfReader(pdf_report_path)
    # # Für jeden Text in jeder Seite:
    # found_text = ""
    # for page in reader.pages:
    #     found_text += page.extract_text() or "" # extract_text kann None zurückgeben
    # assert "NTP Check Results" in found_text
    # assert "URL Check Results" in found_text

    # Check the summary result
    if "URL Check Results" not in summary:
        raise AssertionError("URL Check Results not found in summary")

    if "NTP Check Results" not in summary:
        raise AssertionError("NTP Check Results not found in summary")

    if not pdf_report_path.exists():
        raise AssertionError("PDF report not found")

    # Test the creation of summary json files
    if not (Path(data_dir) / "ntp_results.json").exists():
        raise AssertionError("NTP Results JSON file not found")

    if not (Path(data_dir) / "url_results.json").exists():
        raise AssertionError("URL Results JSON file not found")


@pytest.mark.e2e
def test_gui_workflow(
    q_app: QApplication,
    dummy_app_context: AppContext,
    tmp_path: Path,
) -> None:
    """Test complete GUI workflow including button interactions."""
    gui = CheckConnectGUIRunner(context=dummy_app_context, language="de")
    reports_path = tmp_path / "reports"
    gui.config.set("reports", "directory", str(reports_path))
    # Generate summary from saved json-results by checker.
    manager = ReportManager.from_context(context=dummy_app_context)
    data_dir = manager.get_data_dir()
    print(data_dir)

    gui.test_ntp()
    gui.test_urls()
    gui.generate_reports()
    gui.show_summary()

    log_text = gui.output_log.toPlainText()

    if "NTP" not in log_text:
        raise AssertionError("NTP test not found in log")

    if "Status: 200" not in log_text:
        raise AssertionError("URL test not found in log")

    # Check reports
    if "Reports generated successfully" not in log_text:
        raise AssertionError("Reports generated successfully not found in log")

    # Check summary
    if "summary generated" not in log_text:
        raise AssertionError("summary generated not found in log")

    # Test the creation of reports
    if not (Path(reports_path) / "report.html").exists():
        raise AssertionError("HTML report not found")

    if not (Path(reports_path) / "report.pdf").exists():
        raise AssertionError("PDF report not found")

    # Test the creation of summary json files
    if not (Path(data_dir) / "ntp_results.json").exists():
        raise AssertionError("NTP Results JSON file not found")

    if not (Path(data_dir) / "url_results.json").exists():
        raise AssertionError("URL Results JSON file not found")
