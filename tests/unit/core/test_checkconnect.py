# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Unit tests for the CheckConnect class using pytest and pytest-mock.

This test module validates the functionality of the CheckConnect class,
including successful and failing runs of connectivity checks and report generation.
It employs mocking to isolate the CheckConnect unit from external dependencies
like actual network calls or file system operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from checkconnect.core.checkconnect import CheckConnect
from checkconnect.core.ntp_checker import NTPChecker
from checkconnect.core.url_checker import URLChecker

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from checkconnect.config.appcontext import AppContext


class TestCheckConnect:
    """
    Unit tests for the `CheckConnect` class.

    This test suite comprehensively verifies the functionality of the `CheckConnect` class,
    which is responsible for managing network connectivity checks (NTP and URL)
    and orchestrating report generation. It ensures correct initialization,
    proper execution flow, and robust error handling.
    """

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_checkconnect_initialization(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that `CheckConnect` initializes correctly with the provided application context.

        Verifies that essential attributes like `report_dir`, `ntp_checker`, and `url_checker`
        are properly set up and are instances of their expected classes, reflecting
        correct configuration parsing and component instantiation.

        Args:
        ----
            app_context_fixture (AppContext): A pytest fixture providing a fully
                                              initialized mock `AppContext`.
        """
        checkconnect_instance = CheckConnect(context=app_context_fixture)
        assert "test_reports_from_config" in checkconnect_instance.report_dir
        assert isinstance(checkconnect_instance.ntp_checker, NTPChecker)
        assert isinstance(checkconnect_instance.url_checker, URLChecker)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_run_ntp_checks_success(self, mocker: MockerFixture, app_context_fixture: AppContext) -> None:
        """
        Test the successful execution flow of `CheckConnect.run_ntp_checks()`.

        Mocks the internal `run_ntp_checks` method of the `NTPChecker` and the
        `save_ntp_results` method of the `ReportManager` to ensure that
        `CheckConnect` correctly calls these dependencies, stores results,
        and triggers result saving.

        Args:
        ----
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing a fully
                                              initialized mock `AppContext`.
        """
        checker = CheckConnect(context=app_context_fixture)
        mock_results = ["pool.ntp.org - OK"]

        # Mock the dependency call within CheckConnect
        mock_run_ntp_checks = mocker.patch.object(
            checker.ntp_checker,  # Patch on the ntp_checker instance
            "run_ntp_checks",
            return_value=mock_results,
        )
        mock_save_ntp_results = mocker.patch.object(checker.report_manager, "save_ntp_results")

        checker.run_ntp_checks()

        # Assert that internal methods were called as expected
        mock_run_ntp_checks.assert_called_once_with()
        assert checker.get_ntp_results() == mock_results
        mock_save_ntp_results.assert_called_once_with(mock_results)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_run_ntp_checks_failure(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that `run_ntp_checks` correctly handles and re-raises exceptions.

        Mocks `NTPChecker.run_ntp_checks` to raise an exception, verifying that
        `CheckConnect.run_ntp_checks` propagates this error.

        Args:
        ----
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing a fully
                                              initialized mock `AppContext`.
        """
        checker = CheckConnect(context=app_context_fixture)
        mocker.patch(
            "checkconnect.core.ntp_checker.NTPChecker.run_ntp_checks",
            side_effect=RuntimeError("NTP check failed"),
        )
        # Mock save_ntp_results to ensure it's not called if an exception occurs before
        mocker.patch.object(checker.report_manager, "save_ntp_results")

        with pytest.raises(RuntimeError, match="NTP check failed"):
            checker.run_ntp_checks()

        # Verify save method was not called on failure
        checker.report_manager.save_ntp_results.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_run_url_checks_success(self, mocker: MockerFixture, app_context_fixture: AppContext) -> None:
        """
        Test the successful execution flow of `CheckConnect.run_url_checks()`.

        Mocks the internal `run_url_checks` method of the `URLChecker` and the
        `save_url_results` method of the `ReportManager` to ensure that
        `CheckConnect` correctly calls these dependencies, stores results,
        and triggers result saving.

        Args:
        ----
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing a fully
                                              initialized mock `AppContext`.
        """
        checker = CheckConnect(context=app_context_fixture)
        mock_url_results = ["https://example.com - OK"]

        # Mock the dependency call within CheckConnect
        mock_run_url_checks = mocker.patch.object(
            checker.url_checker,  # Patch on the url_checker instance
            "run_url_checks",
            return_value=mock_url_results,
        )
        mock_save_url_results = mocker.patch.object(checker.report_manager, "save_url_results")

        checker.run_url_checks()

        # Assert that internal methods were called as expected
        mock_run_url_checks.assert_called_once_with()
        assert checker.get_url_results() == mock_url_results
        mock_save_url_results.assert_called_once_with(mock_url_results)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_run_url_checks_failure(self, mocker: MockerFixture, app_context_fixture: AppContext) -> None:
        """
        Test that `run_url_checks` correctly handles and re-raises exceptions.

        Mocks `URLChecker.run_url_checks` to raise an exception, verifying that
        `CheckConnect.run_url_checks` propagates this error.

        Args:
        ----
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing a fully
                                              initialized mock `AppContext`.
        """
        checker = CheckConnect(context=app_context_fixture)
        mocker.patch.object(
            checker.url_checker,
            "run_url_checks",
            side_effect=RuntimeError("URL check failed"),
        )
        # Mock save_url_results to ensure it's not called if an exception occurs before
        mocker.patch.object(checker.report_manager, "save_url_results")

        with pytest.raises(RuntimeError, match="URL check failed"):
            checker.run_url_checks()

        # Verify save method was not called on failure
        checker.report_manager.save_url_results.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["full"], indirect=True)
    def test_run_all_checks_success(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that `run_all_checks` executes both URL and NTP checks successfully
        and saves their results.

        This test verifies the orchestration logic within `run_all_checks` by
        mocking its direct dependencies (`run_url_checks`, `run_ntp_checks`,
        `save_url_results`, and `save_ntp_results`). It ensures that these
        internal methods are called with the correct arguments and in the
        expected sequence.

        Args:
        ----
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing a fully
                                              initialized mock `AppContext`.
        """
        checker = CheckConnect(context=app_context_fixture)

        # Mock the methods that checker.run_all_checks() will call internally.
        # These are the dependencies of run_all_checks, not run_all_checks itself.

        mock_url_results = ["https://example.com - OK"]
        mock_run_url_checks = mocker.patch.object(
            checker.url_checker,  # Patch on the url_checker instance
            "run_url_checks",
            return_value=mock_url_results,
        )

        mock_save_url_results = mocker.patch.object(
            checker.report_manager,  # Patch on the report_manager instance
            "save_url_results",
        )

        mock_ntp_results = ["pool.ntp.org - OK"]
        mock_run_ntp_checks = mocker.patch.object(
            checker.ntp_checker,  # Patch on the ntp_checker instance
            "run_ntp_checks",
            return_value=mock_ntp_results,
        )

        mock_save_ntp_results = mocker.patch.object(
            checker.report_manager,  # Patch on the report_manager instance
            "save_ntp_results",
        )

        # Call the actual method under test
        checker.run_all_checks()

        # Assert that the internal dependencies were called as expected
        mock_run_url_checks.assert_called_once_with()
        mock_run_ntp_checks.assert_called_once_with()
        mock_save_url_results.assert_called_once_with(mock_url_results)
        mock_save_ntp_results.assert_called_once_with(mock_ntp_results)
