# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from checkconnect.exceptions import (
    DirectoryCreationError,
    SummaryDataLoadError,
    SummaryDataSaveError,
    SummaryFormatError,
    SummaryValueError,
)
from checkconnect.reports.report_manager import OutputFormat, ReportDataType, ReportManager

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

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
        return ReportManager.from_params(context=app_context_fixture, data_dir=tmp_path / "output_from_params")

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
    def test_from_params_uses_explicit_output_dir(
        self, app_context_fixture: AppContext, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """
        Test that `from_params` uses the explicit data directory provided.

        Ensures that when an explicit `data_dir` is passed to `from_params`,
        the `ReportManager` uses this path and attempts to ensure its existence.
        """
        mock_ensure_dir = mocker.patch.object(ReportManager, "_ensure_data_directory", return_value=None)

        manager_data_dir = tmp_path / "another_test_data_dir"

        manager = ReportManager.from_params(context=app_context_fixture, data_dir=manager_data_dir)
        # Assert _ensure_data_directory was called with the correct path
        mock_ensure_dir.assert_called_once()

        assert manager.data_dir == manager_data_dir

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_from_context_uses_configured_output_dir(
        self, report_manager_from_context_instance: ReportManager, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        """
        Test that `ReportManager.from_context` uses the configured directory when the context is 'full'.

        Verifies that if the application context is configured with a `data_dir`
        (e.g., from `settings.reports.data_directory`), `from_context` correctly
        uses this path for the report manager's data directory.
        """
        mock_ensure_dir = mocker.patch.object(ReportManager, "_ensure_data_directory", return_value=None)

        app_context = report_manager_from_context_instance.context

        manager = ReportManager.from_context(context=app_context)

        expected_path_from_config = tmp_path / "data"

        mock_ensure_dir.assert_called_once_with(expected_path_from_config)
        assert manager.data_dir == expected_path_from_config

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_from_context_uses_default_output_dir_if_none_in_config(
        self, report_manager_from_context_instance: ReportManager, mocker: MockerFixture
    ) -> None:
        """
        Test that `from_context` uses the default data directory if none is specified in the configuration.

        Ensures that if `settings.reports.data_directory` is not set in the application
        context, the `ReportManager` falls back to its predefined default data path.
        """
        mock_ensure_dir = mocker.patch.object(ReportManager, "_ensure_data_directory", return_value=None)

        app_context = report_manager_from_context_instance.context

        manager = ReportManager.from_context(context=app_context)

        expected_default_path = manager.get_data_dir()
        mock_ensure_dir.assert_called_once_with(expected_default_path)
        assert manager.data_dir == expected_default_path

    @pytest.mark.unit
    def test_ensure_output_directory_creates_dir(
        self, report_manager_from_context_instance: ReportManager, tmp_path: Path
    ) -> None:
        """
        Test that `_ensure_data_directory` creates the directory if it doesn't exist.

        Ensures that the internal helper method correctly creates the target
        data directory and its parents, and returns the verified path.
        """
        # Ensure the directory does not exist to start the test
        test_dir = tmp_path / "new_data"
        assert not test_dir.exists()

        created_path = report_manager_from_context_instance._ensure_data_directory()  # noqa: SLF001
        assert created_path == test_dir
        assert test_dir.is_dir()
        assert test_dir.exists()

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_ensure_output_directory_raises_error_on_failure(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that `DirectoryCreationError` is raised when the data directory cannot be created.

        This test mocks the `Path.mkdir` method to simulate an `OSError` (e.g., permission denied)
        and asserts that `DirectoryCreationError` is raised with the correct message and cause.
        """
        target_path = Path("/nonexistent/path_unwritable")  # A path designed to fail
        with (
            patch.object(Path, "mkdir", side_effect=OSError("Permission denied")),
            pytest.raises(DirectoryCreationError) as excinfo,
        ):
            # Attempt to initialize ReportManager with an uncreatable directory
            ReportManager.from_params(app_context_fixture, target_path)

        # Assert the essential components of the error message
        assert (
            "[mocked] Failed to create directory '/nonexistent/path_unwritable'. Original error: Permission denied"
            in str(excinfo.value)
        )
        assert str(target_path) in str(excinfo.value)
        assert "Original error: Permission denied" in str(excinfo.value)

        # Further assert that the original exception is correctly set as the __cause__
        assert excinfo.value.__cause__ is not None
        assert isinstance(excinfo.value.__cause__, OSError)
        assert "Permission denied" in str(excinfo.value.__cause__)

    @pytest.mark.unit
    def test_summary_format_error_raises(self, report_manager_from_context_instance: ReportManager) -> None:
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
    def test_summary_format_with_enum(self, report_manager_from_context_instance: ReportManager) -> None:
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
        self,
        report_manager_from_params_instance: ReportManager,
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

    @pytest.mark.unit
    def test_save_and_load_results_url(
        self,
        report_manager_from_params_instance: ReportManager,
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

    @pytest.mark.unit
    def test_load_previous_results_combined(
        self,
        report_manager_from_params_instance: ReportManager,
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
        self,
        report_manager_from_params_instance: ReportManager,
    ) -> None:
        """
        Test that `SummaryDataSaveError` is raised when a save operation fails.

        This test mocks the `Path.open` method to simulate an `OSError` during file writing,
        and asserts that `SummaryDataSaveError` is raised with the correct message and cause.
        """
        # Mock Path.open to simulate an OSError (e.g., disk full)
        with patch.object(Path, "open", side_effect=OSError("Disk full")):
            with pytest.raises(SummaryDataSaveError) as excinfo:
                # Any save method relying on _save_json should trigger this
                report_manager_from_params_instance.save_ntp_results(["some data"])

            assert "Could not save ntp results to:" in str(excinfo.value)
            assert isinstance(excinfo.value.__cause__, OSError)

    @pytest.mark.unit
    def test_load_results_error_handling(
        self,
        report_manager_from_params_instance: ReportManager,
    ) -> None:
        """
        Test that `SummaryDataLoadError` is raised when a load operation fails.

        This test simulates a scenario where a results file exists but contains invalid JSON,
        leading to a `json.JSONDecodeError`, and asserts that `SummaryDataLoadError` is raised.
        """
        # Create an empty file so that .exists() returns True, but loading will fail
        ntp_file = (
            report_manager_from_params_instance.get_data_dir()
            / report_manager_from_params_instance._DATA_FILENAMES[ReportDataType.NTP]  # noqa: SLF001
        )
        ntp_file.touch()  # Creates an empty file, which is not valid JSON

        # Mock json.load to simulate a JSONDecodeError (e.g., due to invalid content)
        with patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", doc="{}", pos=1)):
            with pytest.raises(SummaryDataLoadError) as excinfo:
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
