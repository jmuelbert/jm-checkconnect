# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""Integration tests for CheckConnect CLI."""

from __future__ import annotations

import json
import tomllib
import tomli_w

import subprocess
import sys
from pathlib import Path
import platformdirs

import pytest

from checkconnect.config.appcontext import AppContext
from checkconnect.config.logging_manager import LoggingManagerSingleton


class ServerCheckMissingError(Exception):
    def __init__(self, kind_of_server: str):
        super().__init__(f"{kind_of_server} server check message missing")


def generate_config_file(test_env: Path) -> Path:
    """Creates a temporary test configuration file for CheckConnect."""
    config: dict[str, dict[str, Any]] = {
        "logger": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_directory": str(test_env / "logs"),
        },
        "console_handler": {"enabled": False},
        "file_handler": {
            "enabled": True,
            "file_name": "test_file.log",
        },
        "limited_file_handler": {
            "enabled": True,
            "file_name": "limited_test_file.log",
            "max_bytes": 1024,
            "backup_count": 5,
        },
        "gui": {"enabled": True},
        "reports": {"directory": str(test_env)},
        "data": {"directory": str(test_env)},
        "network": {
            "timeout": 5,
            "ntp_servers": ["pool.ntp.org"],
            "urls": ["https://example.com"],
        },
    }

    config_path = test_env / "config.toml"
    with config_path.open("wb") as f:
        tomli_w.dump(config, f)
    return config_path


def get_log_file_from_config(config_file: Path) -> Path:
    """Returns the expected log file path based on the config file."""
    with config_file.open("rb") as f:
        config_data = tomllib.load(f)

    log_dir = Path(config_data.get("logger", {}).get("log_directory", ""))
    file_name = config_data.get("file_handler", {}).get("file_name", "checkconnect.log")

    print("Log directory:", log_dir)
    print("File name:", file_name)
    print("Config file:", config_file)

    return log_dir / file_name


@pytest.fixture
def test_env(tmp_path: Path) -> Path:
    test_dir = tmp_path / "integration_test_dir"
    test_dir.mkdir()
    return test_dir


class TestIntegration:
    """Integration test for CheckConnect CLI."""

    def _clear_log_dir(self, log_dir: Path) -> None:
        for file in log_dir.glob("test_*"):
            file.unlink(missing_ok=True)

    def test_run_execution(self, test_env: Path) -> None:
        """Runs the CheckConnect CLI using subprocess and verifies expected behavior."""
        config_file = generate_config_file(test_env)

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "--config",
            str(config_file),
            "run",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        assert "Checking NTP and URL servers from config!" in result.stdout, "Missing NTP server check in output"
        assert "All checks passed successfully!" in result.stdout, "Missing URL check in output"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        assert "Starting CLI in tests mode" in log_content, "Missing 'Starting CLI in tests mode' in log"
        assert "Starting all checks..." in log_content, "Missing 'Starting all checks...' in log"
        assert "All URL servers checked." in log_content, "Missing 'All URL servers checked.' in log"
        assert "All NTP servers checked." in log_content, "Missing 'All NTP servers checked.' in log"
        assert "All checks completed successfully." in log_content, (
            "Missing 'All checks completed successfully.' in log"
        )

        # Optional cleanup
        log_dir = log_file.parent
        self._clear_log_dir(log_dir)

    def test_report_generation(self, test_env: Path) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        config_file = generate_config_file(test_env)

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "--config",
            str(config_file),
            "report",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        assert "Generating reports" in result.stdout, "Missing 'Generating reports' in output"
        assert "Reports generated successfully" in result.stdout, "Missing 'Reports generated successfully' in output"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        assert "Starting Checkconnect in generate-reports mode." in log_content, (
            "Missing 'Starting Checkconnect in generate-reports mode.' in log"
        )
        assert "Starting all checks..." in log_content, "Missing 'Starting all checks...' in log"
        assert "All URL servers checked." in log_content, "Missing 'All URL servers checked.' in log"
        assert "All NTP servers checked." in log_content, "Missing 'All NTP servers checked.' in log"
        assert "All checks completed successfully." in log_content, (
            "Missing 'All checks completed successfully.' in log"
        )
        assert "Creating HTML report with NTP servers and URLs from config" in log_content, (
            "Missing 'Creating HTML report with NTP servers and URLs from config' in log"
        )
        assert "HTML report generated at" in log_content, "Missing 'HTML report generated at' in log"
        assert "Creating PDF report with NTP servers and URLs from config" in log_content, (
            "Missing 'Creating PDF report with NTP servers and URLs from config' in log"
        )
        assert "PDF report generated at" in log_content, "Missing 'PDF report generated at' in log"

        log_dir = log_file.parent
        self._clear_log_dir(log_dir)

    def test_report_generation_with_cliargs(self, test_env: Path, tmp_path: Path) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        config_file = generate_config_file(test_env)

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "-vv",
            "--language",
            "it",
            "--config",
            str(config_file),
            "report",
            "--reports-dir",
            str(tmp_path),
            "--data-dir",
            str(tmp_path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        assert "Generating reports" in result.stdout, "Missing 'Generating reports' in output"
        assert "Reports generated successfully" in result.stdout, "Missing 'Reports generated successfully' in output"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        print(log_content)

        assert "Starting Checkconnect in generate-reports mode." in log_content, (
            "Missing 'Starting Checkconnect in generate-reports mode.' in log"
        )
        assert "Starting all checks..." in log_content, "Missing 'Starting all checks...' in log"
        assert "All URL servers checked." in log_content, "Missing 'All URL servers checked.' in log"
        assert "All NTP servers checked." in log_content, "Missing 'All NTP servers checked.' in log"
        assert "All checks completed successfully." in log_content, (
            "Missing 'All checks completed successfully.' in log"
        )
        assert "Creating HTML report with NTP servers and URLs from config" in log_content, (
            "Missing 'Creating HTML report with NTP servers and URLs from config' in log"
        )
        assert "HTML report generated at" in log_content, "Missing 'HTML report generated at' in log"
        assert "Creating PDF report with NTP servers and URLs from config" in log_content, (
            "Missing 'Creating PDF report with NTP servers and URLs from config' in log"
        )
        assert "PDF report generated at" in log_content, "Missing 'PDF report generated at' in log"

        log_dir = log_file.parent
        self._clear_log_dir(log_dir)

    def test_summary_generation(self, test_env: Path) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        config_file = generate_config_file(test_env)

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "--config",
            str(config_file),
            "summary",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            # check=True,
            cwd=test_env,
        )

        assert result.returncode == 1, f"Command failed:\n{result.stdout}"

        assert "No saved result found." in result.stdout, "Missing 'No saved result found.'in output"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        assert "Starting Checkconnect in summary mode." in log_content, (
            "Missing 'Starting Checkconnect in summary mode.' in log"
        )

        # Optional cleanup
        log_dir = log_file.parent
        self._clear_log_dir(log_dir)

    def test_summary_generation_with_results(self, test_env: Path) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        config_file = generate_config_file(test_env)

        ntp_results_file = test_env / "ntp_results.json"
        url_results_file = test_env / "url_results.json"

        data_ntp = ["ntp1.example.com - success"]
        data_url = ["https://example.com - ok"]

        ntp_results_file.write_text(json.dumps(data_ntp), encoding="utf-8")
        url_results_file.write_text(json.dumps(data_url), encoding="utf-8")

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "--config",
            str(config_file),
            "summary",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        assert "Starting Checkconnect in summary mode." in result.stdout, (
            "Missing 'Starting Checkconnect in summary mode.'in output"
        )
        assert "Previous results loaded from disk." in result.stdout, (
            "Missing 'Previous results loaded from disk.'in output"
        )
        assert "Results:" in result.stdout, "Missing 'Results:' in output"
        assert "URL Check Results:" in result.stdout, "Missing 'URL Check Results:' in output"
        assert "NTP Check Results:" in result.stdout, "Missing 'Results:' in output"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        assert "Starting Checkconnect in summary mode." in log_content, (
            "Missing 'Starting Checkconnect in summary mode.' in log"
        )
        assert "Previous results loaded from disk." in log_content, (
            "Missing 'Previous results loaded from disk.' in log"
        )

        # Optional cleanup
        log_dir = log_file.parent
        self._clear_log_dir(log_dir)

    def test_summary_generation_with_cliargs(self, test_env: Path, tmp_path: Path) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        config_file = generate_config_file(test_env)

        ntp_results_file = tmp_path / "ntp_results.json"
        url_results_file = tmp_path / "url_results.json"

        data_ntp = [
            "ntp1.example.com - success",
            "ntp2.example.com - success",
            "ntp3.example.com - success",
            "ntp4.example.com - success",
            "ntp5.example.com - success",
            "ntp6.example.com - success",
            "ntp7.example.com - success",
            "ntp8.example.com - success",
            "ntp9.example.com - success",
            "ntp10.example.com - success",
        ]

        data_url = [
            "https://example.com - ok",
            "https://example.org - ok",
            "https://example.net - ok",
            "https://example.edu - ok",
            "https://example.gov - ok",
            "https://example.com - ok",
            "https://example.org - ok",
            "https://example.net - ok",
            "https://example.edu - ok",
            "https://example.gov - ok",
        ]

        ntp_results_file.write_text(json.dumps(data_ntp), encoding="utf-8")
        url_results_file.write_text(json.dumps(data_url), encoding="utf-8")

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "--config",
            str(config_file),
            "summary",
            "--data-dir",
            str(tmp_path),
            "--format",
            "markdown",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        assert "Starting Checkconnect in summary mode." in result.stdout, (
            "Missing 'Starting Checkconnect in summary mode.'in output"
        )
        assert "Previous results loaded from disk." in result.stdout, (
            "Missing 'Previous results loaded from disk.'in output"
        )
        assert "Results:" in result.stdout, "Missing 'Results:' in output"
        assert "## URL Check Results" in result.stdout, "Missing 'URL Check Results:' in output"
        assert "## NTP Check Results" in result.stdout, "Missing 'Results:' in output"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        assert "Starting Checkconnect in summary mode." in log_content, (
            "Missing 'Starting Checkconnect in summary mode.' in log"
        )
        assert "Previous results loaded from disk." in log_content, (
            "Missing 'Previous results loaded from disk.' in log"
        )

        # Optional cleanup
        log_dir = log_file.parent
        self._clear_log_dir(log_dir)

    def test_gui_start(self, test_env: Path) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation
        config_file = generate_config_file(test_env)

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "--config",
            str(config_file),
            "gui",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        # Check for expected log file creation
        log_file = get_log_file_from_config(config_file)
        assert log_file.exists(), f"Log file not created at {log_file}"

        # assert "No saved result found." in result.stdout, "Missing 'No saved result found.'in output"

        # Optional: check contents if needed
        log_content = log_file.read_text(encoding="utf-8")

        assert "Starting CheckConnect GUI..." in log_content, "Missing 'Starting Checkconnect in summary mode.' in log"
        assert "CheckConnect GUI window displayed." in log_content, (
            "Missing 'CheckConnect GUI window displayed.' in log"
        )

        # Optional cleanup
        log_dir = log_file.parent
        self._clear_log_dir(log_dir)
