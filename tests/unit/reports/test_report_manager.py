# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

import json
from math import e
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from checkconnect import __about__

from checkconnect.exceptions import (
    DirectoryCreationError,
    SummaryDataLoadError,
    SummaryDataSaveError,
    SummaryFormatError,
    SummaryValueError,
)
import checkconnect.reports.report_manager as report_manager_module
from checkconnect.reports.report_manager import OutputFormat, ReportDataType, ReportManager

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from structlog.typing import EventDict

    from checkconnect.config.appcontext import AppContext


class TestReportManager:
    """
    Test suite for the `ReportManager` class.

    This class contains unit tests to verify the functionality of the `ReportManager`,
    including directory management, data saving and loading, error handling,
    and summary generation in various formats.
    """

    @pytest.fixture
    def report_manager_from_params_instance(self, app_context_fixture: AppContext, tmp_path: Path) -> ReportManager:
        """
        Fixture for a `ReportManager` instance created via `from_params`.

        This fixture provides a `ReportManager` instance initialized with an
        explicit `data_dir`, simulating the `from_params` factory method.

        Args:
        ----
            app_context_fixture: A pytest fixture providing the application context.
            tmp_path: A pytest fixture providing a temporary directory path.

        Returns:
        -------
            A `ReportManager` instance.
        """
        return ReportManager.from_params(context=app_context_fixture, arg_data_dir=tmp_path / "output_from_params")

    @pytest.fixture
    def report_manager_from_context_instance(self, app_context_fixture: AppContext) -> ReportManager:
        """
        Fixture for a `ReportManager` instance created via `from_context`.

        This fixture provides a `ReportManager` instance initialized using
        the application context, which determines the `data_dir` from settings.

        Args:
        ----
            app_context_fixture: A pytest fixture providing the application context.

        Returns:
        -------
            A `ReportManager` instance.
        """
        return ReportManager.from_context(context=app_context_fixture)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_from_params_uses_explicit_data_dir(self, app_context_fixture: AppContext, tmp_path: Path) -> None:
        """
        Test that `from_params` uses the default directory when none is configured.

        Ensures that if the `reports.directory` setting is missing from the config,
        the `ReportGenerator` falls back to its predefined default output path.
        """
        manager_data_dir = tmp_path / "another_test_data_dir"

        manager = ReportManager.from_params(context=app_context_fixture, arg_data_dir=manager_data_dir)

        assert manager.data_dir == manager_data_dir

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_from_context_uses_configured_data_dir(
        self, report_manager_from_context_instance: ReportManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """
        Test that `ReportGenerator.from_context` uses the configured directory when the context is 'full'.
        """
        app_context = report_manager_from_context_instance.context

        manager = ReportManager.from_context(context=app_context)

        expected_path_from_config = tmp_path / "test_data_from_config"

        assert manager.data_dir == expected_path_from_config

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_from_context_uses_default_data_dir_if_none_in_config(
        self,
        app_context_fixture: AppContext,  # Use this directly, no need for the report_generator_from_context_instance fixture if you're creating it here
        mocker,  # Use mocker from pytest-mock for patching
        caplog_structlog: list[EventDict],  # To capture structlog output
    ) -> None:
        """
        Test that `from_context` uses the default user data directory
        when the configuration does not specify a reports directory.

        Also asserts that the correct log messages are emitted.
        """
        # 1. Arrange (Setup)
        # Ensure config.settings.get returns None for "reports", "directory"
        # The 'simple' app_context_fixture should already have an empty config for this.
        # If not, you might need to mock context.settings.get specifically.
        mocker.patch.object(app_context_fixture.settings, "get", return_value=None)

        # Mock platformdirs.user_data_dir to return a predictable path for testing
        # This prevents creating real directories and ensures test reproducibility across OSes.
        mock_user_data_dir_path = Path("/mocked/user/data/reports/checkconnect")
        mocker.patch(f"{report_manager_module.__name__}.user_data_dir", return_value=str(mock_user_data_dir_path))

        # Mock Path.mkdir since ReportGenerator.__init__ calls it
        # We want to ensure it's called, but not actually create a directory.
        # We'll use a MagicMock for the return value of Path().mkdir()
        mock_mkdir = mocker.patch.object(Path, "mkdir", return_value=None)  # mkdir typically returns None

        # 2. Act (Call the code under test)
        manager = ReportManager.from_context(context=app_context_fixture)

        # 3. Assert (Verify behavior)

        # Assert that the reports_dir is the expected default path
        assert manager.data_dir == mock_user_data_dir_path

        # Assert that mkdir was called correctly
        # It should be called on the Path object representing the default path.
        # The `parents=True` and `exist_ok=True` arguments are important.
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        assert any(
            "Data directory not found in config or invalid. Using default: '{data_dir}'" in e.get("event")
            and e.get("data_dir") == mock_user_data_dir_path
            and e.get("log_level") == "warning"
            for e in caplog_structlog
        )

        assert any(
            "Ensured data directory exists: '{data_dir}'" in e.get("event")
            and e.get("data_dir") == mock_user_data_dir_path
            and e.get("log_level") == "info"
            for e in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_from_context_uses_configured_data_dir(
        self, report_manager_from_context_instance: ReportManager, tmp_path: Path
    ) -> None:
        """
        Test that `ReportManager.from_context` uses the configured directory when the context is 'full'.

        Verifies that if the application context is configured with a `data_dir`
        (e.g., from `settings.reports.data_directory`), `from_context` correctly
        uses this path for the report manager's data directory.
        """
        app_context = report_manager_from_context_instance.context

        manager = ReportManager.from_context(context=app_context)

        expected_path_from_config = tmp_path / "data"

        assert manager.data_dir == expected_path_from_config

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_ensure_data_directory_raises_error_on_failure(
        self, app_context_fixture: AppContext, caplog_structlog: list[EventDict]
    ) -> None:
        """
        Test that `DirectoryCreationError` is raised when the data directory cannot be created.

        This test mocks the `Path.mkdir` method to simulate an `OSError` (e.g., permission denied)
        and asserts that `DirectoryCreationError` is raised with the correct message and cause.
        """
        # Define a target path that will definitely cause an OSError
        target_path = Path("/nonexistent/path_unwritable")

        # Define the expected error message from the OSError
        os_error_message = "Permission denied"

        with (
            # Patch Path.mkdir to simulate an OSError
            patch.object(Path, "mkdir", side_effect=OSError(os_error_message)),
            # Assert that DirectoryCreationError is raised
            pytest.raises(DirectoryCreationError) as excinfo,
        ):
            # Attempt to initialize ReportManager with an uncreatable directory
            ReportManager.from_params(context=app_context_fixture, arg_data_dir=target_path)

        # Assert the essential components of the error message
        assert "[mocked] Failed to create data directory: '/nonexistent/path_unwritable': Permission denied" in str(
            excinfo.value
        )
        assert os_error_message in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, OSError)

        assert any(
            e.get("event") == "[mocked] Failed to create data directory: '{data_dir}'"
            and e.get("data_dir") == target_path
            and e.get("log_level") == "error"
            for e in caplog_structlog
        )

    @pytest.mark.unit
    def test_summary_format_error_raises(
        self,
        report_manager_from_context_instance: ReportManager,
    ) -> None:
        """
        Test that `SummaryFormatError` is raised when an invalid summary format string is provided.
        """
        invalid_format_string = "invalid_format"
        with pytest.raises(SummaryFormatError) as excinfo:
            report_manager_from_context_instance.get_summary([], [], invalid_format_string)

        expected_error_message = (
            f"Invalid format specified. Use 'text', 'markdown', or 'html' instead of {invalid_format_string}."
        )

        assert expected_error_message in str(excinfo.value)

    @pytest.mark.unit
    def test_summary_format_with_enum(
        self,
        report_manager_from_context_instance: ReportManager,
    ) -> None:
        """
        Test that `get_summary` works correctly when `OutputFormat` enum values are used.

        This test ensures that using the `OutputFormat` enum does not raise an error
        and that the summary content is as expected for a valid format.
        """
        summary = report_manager_from_context_instance.get_summary([], [], OutputFormat.text)
        assert "URL Check Results" in summary
        assert "NTP Check Results" in summary

    @pytest.mark.unit
    def test_save_and_load_results_ntp(
        self, report_manager_from_params_instance: ReportManager, caplog_structlog: list[EventDict]
    ) -> None:
        """
        Test the saving and loading of NTP results.

        This test verifies that NTP results can be correctly saved to a JSON file
        and subsequently loaded back, ensuring data integrity.
        """
        data_ntp = ["ntp1.example.com - success"]

        # Call the specific save_ntp_results method
        report_manager_from_params_instance.save_ntp_results(data_ntp)

        # Construct the expected file path using the internal mapping
        ntp_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.NTP]  # noqa: SLF001
        )
        assert ntp_file.exists()

        # Verify the content of the saved file
        with ntp_file.open(encoding="utf-8") as f:
            assert json.load(f) == data_ntp

        # Call the specific load_ntp_results method
        loaded_ntp_data = report_manager_from_params_instance.load_ntp_results()
        assert loaded_ntp_data == data_ntp

        assert any(
            "Loaded {data_type.value} results from: {file_path}" in event.get("event")
            and event.get("data_type_value") == "ntp"
            and event.get("file_path") == ntp_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        assert any(
            "Results for '{data_type.value}' saved to disk: '{output_path}'" in event.get("event")
            and event.get("data_type_value") == "ntp"
            and event.get("file_path") == ntp_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

    @pytest.mark.unit
    def test_save_and_load_results_url(
        self, report_manager_from_params_instance: ReportManager, caplog_structlog: list[EventDict]
    ) -> None:
        """
        Test the saving and loading of URL results.

        This test verifies that URL results can be correctly saved to a JSON file
        and subsequently loaded back, ensuring data integrity.
        """
        data_url = ["https://example.com - ok"]

        # Call the specific save_url_results method
        report_manager_from_params_instance.save_url_results(data_url)

        # Construct the expected file path using the internal mapping
        url_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.URL]  # noqa: SLF001
        )
        assert url_file.exists()

        # Verify the content of the saved file
        with url_file.open(encoding="utf-8") as f:
            assert json.load(f) == data_url

        # Call the specific load_url_results method
        loaded_url_data = report_manager_from_params_instance.load_url_results()
        assert loaded_url_data == data_url

        assert any(
            "Loaded {data_type.value} results from: {file_path}" in event.get("event")
            and event.get("data_type_value") == "url"
            and event.get("file_path") == url_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        assert any(
            "Results for '{data_type.value}' saved to disk: '{output_path}'" in event.get("event")
            and event.get("data_type_value") == "url"
            and event.get("file_path") == url_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

    @pytest.mark.unit
    def test_load_previous_results_combined(
        self, report_manager_from_params_instance: ReportManager, caplog_structlog: list[EventDict]
    ) -> None:
        """
        Test the combined loading of previous NTP and URL results.

        This test ensures that `load_previous_results` correctly retrieves data
        saved by individual save methods.
        """
        data_ntp = ["ntp1.example.com - success"]
        data_url = ["https://example.com - ok"]

        # Save the data using the specific methods
        report_manager_from_params_instance.save_ntp_results(data_ntp)
        report_manager_from_params_instance.save_url_results(data_url)

        # Call the combined load_previous_results method
        ntp, url = report_manager_from_params_instance.load_previous_results()
        assert ntp == data_ntp
        assert url == data_url

        # NTP - Data
        # Construct the expected file path using the internal mapping
        ntp_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.NTP]  # noqa: SLF001
        )
        assert any(
            "Loaded {data_type.value} results from: {file_path}" in event.get("event")
            and event.get("data_type_value") == "ntp"
            and event.get("file_path") == ntp_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        assert any(
            "Results for '{data_type.value}' saved to disk: '{output_path}'" in event.get("event")
            and event.get("data_type_value") == "ntp"
            and event.get("file_path") == ntp_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        # URL - Data
        # Construct the expected file path using the internal mapping
        url_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.URL]  # noqa: SLF001
        )
        assert any(
            "Loaded {data_type.value} results from: {file_path}" in event.get("event")
            and event.get("data_type_value") == "url"
            and event.get("file_path") == url_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        assert any(
            "Results for '{data_type.value}' saved to disk: '{output_path}'" in event.get("event")
            and event.get("data_type_value") == "url"
            and event.get("file_path") == url_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        assert any(
            "Loaded {data_type.value} results from: {file_path}" in event.get("event")
            and event.get("data_type_value") == "ntp"
            and event.get("file_path") == ntp_file
            and event.get("log_level") == "debug"
            for event in caplog_structlog
        )

        assert any(
            "Previous results loaded from disk." in event.get("event") and event.get("log_level") == "info"
            for event in caplog_structlog
        )

    @pytest.mark.unit
    def test_results_exists(
        self,
        report_manager_from_params_instance: ReportManager,
    ) -> None:
        """
        Test the `results_exists` method.

        This test verifies that `results_exists` accurately reports the presence
        of both NTP and URL result files.
        """
        # Initially, no files should exist
        assert not report_manager_from_params_instance.results_exists()

        # Save only NTP results
        report_manager_from_params_instance.save_ntp_results(["ntp1 - ok"])
        assert not report_manager_from_params_instance.results_exists()  # Only NTP file exists, should still be False

        # Save URL results
        report_manager_from_params_instance.save_url_results(["url1 - ok"])
        assert report_manager_from_params_instance.results_exists()  # Both files exist, should be True

        # Delete one file and check again
        ntp_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.NTP]  # noqa: SLF001
        )
        ntp_file.unlink()
        assert not report_manager_from_params_instance.results_exists()

    @pytest.mark.unit
    def test_save_results_error_handling(
        self, report_manager_from_params_instance: ReportManager, caplog_structlog: list[EventDict]
    ) -> None:
        """
        Test that `SummaryDataSaveError` is raised when a save operation fails.

        This test mocks the `Path.open` method to simulate an `OSError` during file writing,
        and asserts that `SummaryDataSaveError` is raised with the correct message and cause.
        """
        # Mock Path.open to simulate an OSError (e.g., disk full)
        # Define the expected error message from the OSError
        os_error_message = "Disk full"

        with patch.object(Path, "open", side_effect=OSError(os_error_message)):
            with pytest.raises(SummaryDataSaveError) as excinfo:
                # Any save method relying on _save_json should trigger this
                report_manager_from_params_instance.save_ntp_results(["some data"])

        # Assertions for the raised exception
        assert "Could not save ntp results to:" in str(excinfo.value)
        assert "Could not save ntp results to:" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, OSError)

        assert any(
            "Could not save '{data_type.value}' results due to an unexpected error." in event["event"]
            and event.get("data_type_value") == "ntp"
            and event.get("log_level") == "error"
            for event in caplog_structlog
        )

    @pytest.mark.unit
    def test_load_results_error_handling(
        self, report_manager_from_params_instance: ReportManager, caplog_structlog: list[EventDict]
    ) -> None:
        """
        Test that `SummaryDataLoadError` is raised when a load operation fails.

        This test simulates a scenario where a results file exists but contains invalid JSON,
        leading to a `json.JSONDecodeError`, and asserts that `SummaryDataLoadError` is raised.
        """
        json_error_message = "Invalid JSON"
        # Create an empty file so that .exists() returns True, but loading will fail
        ntp_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.NTP]  # noqa: SLF001
        )
        ntp_file.touch()  # Creates an empty file, which is not valid JSON

        # Mock json.load to simulate a JSONDecodeError (e.g., due to invalid content)
        with (
            patch("json.load", side_effect=json.JSONDecodeError(json_error_message, doc="{}", pos=1)),
            pytest.raises(SummaryDataLoadError) as excinfo,
        ):
            report_manager_from_params_instance.load_ntp_results()

        assert "Failed to load ntp results from:" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, json.JSONDecodeError)

    @pytest.mark.parametrize(
        ("fmt", "expected_title_prefix"),
        [
            (OutputFormat.text, "[mocked] NTP Check Results:"),
            (OutputFormat.markdown, "## [mocked] NTP Check Results"),
            (OutputFormat.html, "<h2>[mocked] NTP Check Results</h2>"),
        ],
    )
    def test_summary_formats(
        self,
        report_manager_from_params_instance: ReportManager,
        fmt: OutputFormat,
        expected_title_prefix: str,
    ) -> None:
        """
        Test the various summary output formats (text, markdown, html).

        This parameterized test verifies that the `get_summary` method produces
        correctly formatted output for different `OutputFormat` enum values.

        Args:
        ----
            report_manager_from_params_instance: The `ReportManager` instance under test.
            fmt: The `OutputFormat` enum value to test.
            expected_title_prefix: The expected prefix for the NTP results section
                                   based on the `fmt`.
        """
        ntp_results = ["ntp1 - ok"]
        url_results = ["https://test.com - reachable"]

        summary = report_manager_from_params_instance.get_summary(ntp_results, url_results, summary_format=fmt)

        if expected_title_prefix not in summary:
            msg = f"Expected '{expected_title_prefix}' not found in summary: {summary}"
            raise SummaryValueError(msg)

        # Further assertions to ensure the content and overall structure are correct for each format
        if fmt == OutputFormat.text:
            assert "[mocked] URL Check Results:\nhttps://test.com - reachable" in summary
            assert "[mocked] NTP Check Results:\nntp1 - ok" in summary
            assert summary.endswith("ntp1 - ok")  # Check for exact string at the end as no trailing newlines
        elif fmt == OutputFormat.markdown:
            assert "## [mocked] URL Check Results\n- https://test.com - reachable" in summary
            assert "## [mocked] NTP Check Results\n- ntp1 - ok" in summary
            assert summary.endswith("- ntp1 - ok")
        elif fmt == OutputFormat.html:
            assert "<html><body>" in summary
            assert "</body></html>" in summary
            assert "<h2>[mocked] URL Check Results</h2><ul><li>https://test.com - reachable</li></ul>" in summary
            assert "<h2>[mocked] NTP Check Results</h2><ul><li>ntp1 - ok</li></ul>" in summary
            assert "<br><br>" in summary  # Check for the separator between sections
