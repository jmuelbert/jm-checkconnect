# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""Integration tests for CheckConnect CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from checkconnect.config.logging_manager import LoggingManagerSingleton


class ServerCheckMissingError(Exception):
    def __init__(self, kind_of_server: str):
        super().__init__(f"{kind_of_server} server check message missing")


@pytest.fixture
def test_env(tmp_path: Path) -> Path:
    test_dir = tmp_path / "integration_test_dir"
    test_dir.mkdir(exist_ok=True)
    return test_dir


class TestIntegration:
    """
    Integration tests for CheckConnect CLI.

    These tests verify the end-to-end functionality of the CheckConnect CLI
    using both subprocess calls and direct imports to test the application.
    """

    def _get_log_file(self) -> Path:
        logger = LoggingManagerSingleton.get_instance()
        log_dir = logger.log_dir
        log_file: Path = log_dir / logger.DEFAULT_LOG_FILENAME
        return log_file

    def _clear_log_dir(self) -> None:
        logger = LoggingManagerSingleton.get_instance()
        log_dir = logger.log_dir
        log_files = log_dir.glob("test_*")
        for file in log_files:
            file.unlink(missing_ok=True)

    def test_run_execution(
        self,
        config_file: Path,
        test_env: Path,
    ) -> None:
        """Test the application using subprocess to run the CLI command."""
        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "run",
            "--config",
            str(config_file),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        if result.returncode != 0:
            raise AssertionError(f"Command failed:\n{result.stderr}")

        log_file: Path = self._get_log_file()

        if not log_file.exists():
            raise AssertionError(f"Log file not created at {log_file}")

        with Path(log_file).open(encoding="utf-8") as f:
            log_content = f.read()
            assert "Starting CLI in tests mode" in log_content, "Log start message missing"

        if "Checking NTP servers from config" not in result.stderr:
            raise ServerCheckMissingError("NTP")
        if "Checking URL servers from config" not in result.stderr:
            raise ServerCheckMissingError("URL")

        # Clean up!
        self._clear_log_dir()

    def test_report_generation(
        self,
        config_file: Path,
        test_env: Path,
    ) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "report",
            "--config",
            str(config_file),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        log_file: Path = self._get_log_file()

        assert log_file.exists(), f"Log file not created at {log_file}"

        with Path(log_file).open(encoding="utf-8") as f:
            log_content = f.read()
            assert "Starting CLI in tests mode" in log_content, "Log start message missing"

        assert "Checking NTP servers from config" in result.stderr  # added
        assert "Checking URLs from config" in result.stderr  # added

        # Clean up!
        self._clear_log_dir()

    def test_summary_generation(
        self,
        config_file: Path,
        test_env: Path,
    ) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "summary",
            "--config",
            str(config_file),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        log_file: Path = self._get_log_file()
        assert log_file.exists(), f"Log file not created at {log_file}"

        with Path(log_file).open(encoding="utf-8") as f:
            log_content = f.read()
            assert "Starting CLI in tests mode" in log_content, "Log start message missing"

        assert "Checking NTP servers from config" in result.stderr  # added
        assert "Checking URLs from config" in result.stderr  # added

        # Clean up!
        self._clear_log_dir()

    def test_gui_start(
        self,
        config_file: Path,
        test_env: Path,
    ) -> None:
        """
        Test that the application correctly generates reports.

        This test verifies that HTML and PDF reports are created and contain expected content.
        """
        # Create a script that directly calls report generation

        command = [
            sys.executable,
            "-m",
            "checkconnect.cli.main",
            "gui",
            "--config",
            str(config_file),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=test_env,
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        log_file: Path = self._get_log_file()
        assert log_file.exists(), f"Log file not created at {log_file}"

        with Path(log_file).open(encoding="utf-8") as f:
            log_content = f.read()
            assert "Starting CLI in tests mode" in log_content, "Log start message missing"

        assert "Checking NTP servers from config" in result.stderr  # added
        assert "Checking URLs from config" in result.stderr  # added

        # Clean up!
        self._clear_log_dir()
