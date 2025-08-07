# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Unit tests for the NTPChecker class.

This module contains comprehensive unit tests for the `NTPChecker` class and
its associated configuration model `NTPCheckerConfig`. It verifies the
correct initialization, validation, and execution of NTP connectivity checks,
including handling various success and failure scenarios.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Final

import ntplib
import pytest
from pydantic import ValidationError

from checkconnect.core.ntp_checker import NTPChecker, NTPCheckerConfig

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from structlog.typing import EventDict

    from checkconnect.config.appcontext import AppContext


@pytest.fixture
def valid_ntp_config(app_context_fixture: AppContext) -> NTPCheckerConfig:
    """
    Fixture that returns a valid NTPCheckerConfig instance.

    This fixture provides a pre-configured `NTPCheckerConfig` object with
    example NTP server addresses and a timeout, suitable for various tests.

    Args:
        app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.

    Returns:
        NTPCheckerConfig: An instance of `NTPCheckerConfig` with valid settings.
    """
    return NTPCheckerConfig(
        context=app_context_fixture,
        ntp_servers=["time.google.com", "8.8.8.8"],
        timeout=5,
    )


@pytest.fixture
def mock_success(mocker: MockerFixture) -> str:
    """
    Mocks a successful `ntplib.NTPClient.request` call.

    This fixture sets up a mock for the `ntplib.NTPClient.request` method
    to simulate a successful NTP response.

    Args:
        mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.

    Returns:
        str: A string "NTP:" indicating the mock's purpose (though not directly used in assertions).
    """
    mock_ntp_response = mocker.Mock()
    mock_ntp_response.tx_time = 1234567890.12345
    mocker.patch("ntplib.NTPClient.request", return_value=mock_ntp_response)

    return "NTP:"


class TestNTPCheckerConfig:
    """
    Test cases for the `NTPCheckerConfig` Pydantic model.

    This class verifies that `NTPCheckerConfig` handles valid and invalid
    input correctly, ensuring proper data validation and error handling
    for NTP server lists and timeout values.
    """

    @pytest.mark.unit
    def test_valid_config(self, valid_ntp_config: NTPCheckerConfig) -> None:
        """
        Test the successful creation of a valid `NTPCheckerConfig` instance.

        Verifies that the `ntp_servers` and `timeout` attributes are correctly
        assigned from the provided valid configuration.

        Args:
            valid_ntp_config (NTPCheckerConfig): A pytest fixture providing a valid config.
        """
        expected_timeout: Final[int] = 5
        expected_servers_count: Final[int] = 2

        checker = NTPChecker(config=valid_ntp_config)
        assert isinstance(checker, NTPChecker)

        assert len(checker.config.ntp_servers) == expected_servers_count
        assert checker.config.ntp_servers == ["time.google.com", "8.8.8.8"]
        assert checker.config.timeout == expected_timeout

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_direct_config_initialization(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test `NTPCheckerConfig` instantiation when parameters are provided directly.

        Verifies that the configuration object is correctly created from explicit
        `ntp_servers` and `timeout` arguments along with the context.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        expected_timeout: Final[int] = 10

        config = NTPCheckerConfig(
            ntp_servers=["time.cloudflare.com"],
            timeout=expected_timeout,
            context=app_context_fixture,
        )
        assert isinstance(config, NTPCheckerConfig)
        assert config.ntp_servers == ["time.cloudflare.com"]
        assert config.timeout == expected_timeout
        assert config.context == app_context_fixture

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_negative_timeout(self, app_context_fixture: AppContext) -> None:
        """
        Test that a negative timeout value raises a `ValidationError`.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            NTPCheckerConfig(
                ntp_servers=["time.google.com"],
                timeout=-10,
                context=app_context_fixture,
            )
        assert "Timeout must be a positive integer" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_invalid_timeout_type(self, app_context_fixture: AppContext) -> None:
        """
        Test that an invalid type for timeout (e.g., string) raises a `ValidationError`.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            NTPCheckerConfig(
                ntp_servers=["pool.ntp.org"],
                timeout="not-an-int",  # type: ignore[arg-type]
                context=app_context_fixture,
            )
        assert "Input should be a valid integer" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_invalid_ntp_server_format(self, app_context_fixture: AppContext) -> None:
        """
        Test that an invalid NTP server format raises a `ValidationError`.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            NTPCheckerConfig(
                ntp_servers=["not-a-url"],
                timeout=5,
                context=app_context_fixture,
            )
        assert "ntp_servers" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_empty_ntp_servers_list(self, app_context_fixture: AppContext) -> None:
        """
        Test that an empty list of NTP servers raises a `ValidationError`.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            NTPCheckerConfig(
                ntp_servers=[],
                timeout=5,
                context=app_context_fixture,
            )
        assert "ntp_servers" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("test_input", "expected_error_substring"),
        [
            (
                {"ntp_servers": "not-a-list", "timeout": 5},
                "Input should be a valid list",
            ),
            (
                {"ntp_servers": ["pool.ntp.org"], "timeout": "not-an-int"},
                "Input should be a valid integer",
            ),
            (
                {"ntp_servers": ["pool.ntp.org"], "timeout": 0},
                "Timeout must be a positive integer",
            ),
            (
                {"ntp_servers": ["not-a-url"], "timeout": 5},
                "Invalid NTP servers:",
            ),
        ],
    )
    @pytest.mark.unit
    def test_config_validation_errors(
        self,
        test_input: dict[str, Any],
        expected_error_substring: str,
        app_context_fixture: AppContext,  # Included as it's typically needed for context-related features
    ) -> None:
        """
        Test various validation error scenarios for `NTPCheckerConfig`.

        This parameterized test ensures that `NTPCheckerConfig` correctly
        raises `ValidationError` for invalid inputs, such as incorrect data types,
        out-of-range values, or malformed NTP server addresses.

        Args:
            test_input (dict[str, Any]): A dictionary containing parameters to
                                        pass to `NTPCheckerConfig`.
            expected_error_substring (str): A substring expected to be present
                                            in the `ValidationError` message.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            # We need to include 'context' in test_input if it's a required field for NTPCheckerConfig
            # or handle it separately if it's passed during instantiation, not validation.
            # Based on the NTPCheckerConfig model, 'context' is a field, so it needs to be provided.
            # However, for testing *validation* of other fields, we can provide a dummy context.
            # The test_input dictionary usually covers the fields being tested for validation.
            # So, we modify this part to always include a valid context.
            NTPCheckerConfig(
                **test_input,
                context=app_context_fixture,
            )
        assert expected_error_substring in str(exc_info.value)


class TestNTPChecker:
    """
    Test cases for the `NTPChecker` class.

    This class contains tests for the core functionality of `NTPChecker`,
    including successful NTP requests, handling network errors, and
    processing multiple servers. It leverages mocks to isolate network
    interactions.
    """

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_ntp_checker_integration(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test `NTPChecker`'s integration with mocked `ntplib.NTPClient.request`.

        This test verifies that `NTPChecker` can successfully perform an NTP check
        when `ntplib.NTPClient.request` is mocked to return a valid response.
        It also checks for appropriate log messages, including the `[mocked]` prefix.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """

        mock_response = mocker.Mock()
        mock_response.tx_time = 1713450000.0
        mocker.patch("ntplib.NTPClient.request", return_value=mock_response)

        checker = NTPChecker.from_params(
            context=app_context_fixture,
            ntp_servers=["pool.ntp.org"],
            timeout=5,
        )

        results = checker.run_ntp_checks()

        assert isinstance(results, list)
        assert len(results) == 1
        assert all(isinstance(r, str) for r in results)

        assert "[mocked] Successfully retrieved time from pool.ntp.org - Time:" in results[0]

        # Check logger output for info messages with the '[mocked]' prefix
        assert any(
            record["event"] == "[mocked] Checking NTP servers..."
            and record["log_level"] == "info"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "pool.ntp.org"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Successfully retrieved time from server"
            and record["log_level"] == "debug"
            and record["server"] == "pool.ntp.org"
            for record in caplog_structlog)

        assert any(
            record["event"] == "[mocked] All NTP servers checked."
            and record["log_level"] == "info"
            for record in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_initialization(self, valid_ntp_config: NTPCheckerConfig) -> None:
        """
        Test `NTPChecker` initialization.

        Verifies that an `NTPChecker` instance can be created and that its
        `config` attribute is correctly set.

        Args:
            valid_ntp_config (NTPCheckerConfig): A pytest fixture providing a valid config.
        """
        checker = NTPChecker(config=valid_ntp_config)

        assert isinstance(checker, NTPChecker)
        assert checker.config == valid_ntp_config
        assert checker.config.context == valid_ntp_config.context

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_from_params(self, app_context_fixture: AppContext) -> None:
        """
        Test the `NTPChecker.from_params` classmethod.

        Verifies that this convenience constructor correctly creates an
        `NTPChecker` instance with the specified parameters, which are
        then wrapped into an `NTPCheckerConfig`, and that the context is passed.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        expected_timeout: Final[int] = 5
        checker = NTPChecker.from_params(
            ntp_servers=["pool.ntp.org"],
            timeout=5,
            context=app_context_fixture,
        )
        assert isinstance(checker, NTPChecker)
        assert len(checker.config.ntp_servers) == 1
        assert checker.config.timeout == expected_timeout
        assert checker.config.context == app_context_fixture

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_run_ntp_checks_successful(
        self,
        mocker: MockerFixture,
        valid_ntp_config: NTPCheckerConfig,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test `run_ntp_checks` when all NTP requests are successful.

        Mocks `ntplib.NTPClient.request` to always return a successful response
        and verifies that the results list contains success messages for all servers.
        Also checks for expected log messages including the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            valid_ntp_config (NTPCheckerConfig): A pytest fixture providing a valid config.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        expected_results_count: Final[int] = 2
        # caplog.set_level(10)  # Set log level to DEBUG

        mock_response = mocker.MagicMock()
        mock_response.tx_time = time.time()
        mocker.patch("ntplib.NTPClient.request", return_value=mock_response)

        checker = NTPChecker(config=valid_ntp_config)
        results = checker.run_ntp_checks()

        assert len(results) == expected_results_count
        assert "[mocked] Successfully retrieved time from time.google.com" in results[0]
        assert "[mocked] Successfully retrieved time from 8.8.8.8" in results[1]

        # Check logger output
        assert any(
            record["event"] == "[mocked] Checking NTP servers..."
            and record["log_level"] == "info"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "time.google.com"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "8.8.8.8"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Successfully retrieved time from server"
            and record["log_level"] == "debug"
            and record["server"] == "time.google.com"
            for record in caplog_structlog)

        assert any(
            record["event"] == "[mocked] Successfully retrieved time from server"
            and record["log_level"] == "debug"
            and record["server"] == "8.8.8.8"
            for record in caplog_structlog)

        assert any(
            record["event"] == "[mocked] All NTP servers checked."
            and record["log_level"] == "info"
            for record in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_run_ntp_checks_request_error(
        self,
        mocker: MockerFixture,
        valid_ntp_config: NTPCheckerConfig,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test `run_ntp_checks` when an `ntplib.NTPException` occurs during a request.

        Mocks `ntplib.NTPClient.request` to raise an `NTPException` and verifies
        that the result reflects the error and an appropriate log message is emitted
        with the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            valid_ntp_config (NTPCheckerConfig): A pytest fixture providing a valid config.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        expected_results_count: Final[int] = 2

        mocker.patch(
            "ntplib.NTPClient.request",
            side_effect=ntplib.NTPException("Test error"),
        )

        checker = NTPChecker(config=valid_ntp_config)
        results = checker.run_ntp_checks()

        assert len(results) == expected_results_count  # Two servers in valid_ntp_config
        assert "[mocked] Error retrieving time from NTP server time.google.com: Test error" in results[0]
        assert "[mocked] Error retrieving time from NTP server 8.8.8.8: Test error" in results[1]

        # Check logger output for error messages
        assert any (
            record["event"] == "[mocked] Checking NTP servers..."
            and record["log_level"] == "info"
            for record in caplog_structlog
        )

        # Test with time.google.com
        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "time.google.com"
            for record in caplog_structlog
        )

        assert any(
            "exc_info" in record
            and record["event"] == "[mocked] Error retrieving time from NTP server"
            and record["log_level"] == "error"
            and record["server"] == "time.google.com"
            and isinstance(record["exc_info"], ntplib.NTPException)
            and "Test error" in str(record["exc_info"])
            for record in caplog_structlog
        )

        # Test with 8.8.8.8
        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "8.8.8.8"
            for record in caplog_structlog
        )

        assert any(
            "exc_info" in record
            and record["event"] == "[mocked] Error retrieving time from NTP server"
            and record["log_level"] == "error"
            and record["server"] == "8.8.8.8"
            and isinstance(record["exc_info"], ntplib.NTPException)
            and "Test error" in str(record["exc_info"])
            for record in caplog_structlog
        )

        # All done.
        assert any(
            record["event"] == "[mocked] All NTP servers checked."
            and record["log_level"] == "info"
            for record in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_ntp_checker_with_context(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test `NTPChecker` functionality with a specific server configured via `from_params`.

        Verifies successful NTP check and associated log messages including the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """

        mock_response = mocker.Mock()
        mock_response.tx_time = 1234567890
        mock_client = mocker.Mock()
        mock_client.request.return_value = mock_response
        mocker.patch("ntplib.NTPClient", return_value=mock_client)

        ntp_checker = NTPChecker.from_params(
            context=app_context_fixture,
            ntp_servers=["pool.ntp.org"],
            timeout=5,
        )

        results = ntp_checker.run_ntp_checks()

        assert len(results) == 1
        assert "[mocked] Successfully retrieved time from pool.ntp.org " in results[0]

        # Check logger output
        assert any(
            event["event"] == "[mocked] Checking NTP servers..."
            and event["log_level"] == "info"
            for event in caplog_structlog
        )

        assert any(
            event["event"] == "[mocked] Checking NTP server"
            and event["log_level"] == "debug"
            and event["server"] == "pool.ntp.org"
            for event in caplog_structlog
        )

        assert any(
            event["event"] == "[mocked] Successfully retrieved time from server"
            and event["log_level"] == "debug"
            and event["server"] == "pool.ntp.org"
            for event in caplog_structlog)

        assert any(
            event["event"] == "[mocked] All NTP servers checked."
            and event["log_level"] == "info"
            for event in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_ntp_checker_with_general_failure(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test `NTPChecker`'s error handling for a general exception during NTP request.

        Mocks `ntplib.NTPClient.request` to raise a generic `Exception` and
        verifies that the result indicates an error and an error log is generated
        with the `[mocked]` prefix and correct exception info.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """

        mock_request = mocker.patch("ntplib.NTPClient.request")
        mock_request.side_effect = Exception("Timeout!")

        checker = NTPChecker.from_params(
            context=app_context_fixture,
            ntp_servers=["fake.ntp.org"],
            timeout=2,
        )

        results = checker.run_ntp_checks()

        assert len(results) == 1
        assert "[mocked] An unexpected error occurred while checking NTP server fake.ntp.org: Timeout!" in results[0]

        # Check logger output (the exception will be caught and logged by logger.exception)

        assert any (
            record["event"] == "[mocked] Checking NTP servers..."
            and record["log_level"] == "info"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "fake.ntp.org"
            for record in caplog_structlog
        )

        assert any(
            "exc_info" in record
            and record["event"] == "[mocked] An unexpected error occurred while checking NTP server"
            and record["log_level"] == "error"
            and record["server"] == "fake.ntp.org"
            and isinstance(record["exc_info"], Exception)
            and "Timeout!" in str(record["exc_info"])
            for record in caplog_structlog
        )

        assert any(
           record["event"] == "[mocked] All NTP servers checked."
           and record["log_level"] == "info"
           for record in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_multiple_ntp_servers(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test checking multiple NTP servers with mixed results (success, failure, success).

        This test simulates a scenario where some NTP server checks succeed and others fail,
        and verifies that `NTPChecker` correctly records all outcomes and logs them
        appropriately with the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        expected_results_count: Final[int] = 3

        # Mock for successful NTP response
        mock_success_response = mocker.Mock()
        mock_success_response.tx_time = 1234567890.12345

        # Mock the .request method of NTPClient to return mixed results
        mocker.patch(
            "ntplib.NTPClient.request",
            side_effect=[
                mock_success_response,  # 1st server: Success
                ntplib.NTPException("Failed to connect"),  # 2nd server: Failure
                mock_success_response,  # 3rd server: Success
            ],
        )

        config = NTPCheckerConfig(
            ntp_servers=[
                "pool.ntp.org",
                "fake.ntp.org",
                "8.8.8.8",
            ],
            timeout=5,
            context=app_context_fixture,
        )
        checker = NTPChecker(config=config)
        results = checker.run_ntp_checks()

        assert len(results) == expected_results_count
        assert "[mocked] Successfully retrieved time from pool.ntp.org" in results[0]
        assert "[mocked] Error retrieving time from NTP server fake.ntp.org: Failed to connect" in results[1]
        assert "[mocked] Successfully retrieved time from 8.8.8.8" in results[2]

        # Check logger output for mixed results
        assert any(
            record["event"] == "[mocked] Checking NTP servers..."
            and record["log_level"] == "info"
            for record in caplog_structlog
        )

        # Server pool.ntp.org
        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "pool.ntp.org"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Successfully retrieved time from server"
            and record["log_level"] == "debug"
            and record["server"] == "pool.ntp.org"
            for record in caplog_structlog
        )

        # Server fake.ntp.org
        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "fake.ntp.org"
            for record in caplog_structlog
        )

        assert any(
            "exc_info" in record
            and record["event"] == "[mocked] Error retrieving time from NTP server"
            and record["log_level"] == "error"
            and record["server"] == "fake.ntp.org"
            and isinstance(record["exc_info"], ntplib.NTPException)
            and "Failed to connect" in str(record["exc_info"])
            for record in caplog_structlog
        )

        # Server 8.8.8.8
        assert any(
            record["event"] == "[mocked] Checking NTP server"
            and record["log_level"] == "debug"
            and record["server"] == "8.8.8.8"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Successfully retrieved time from server"
            and record["log_level"] == "debug"
            and record["server"] == "8.8.8.8"
            for record in caplog_structlog
        )

        # All done
        assert any(
            record["event"] == "[mocked] All NTP servers checked."
            and record["log_level"] == "info"
            for record in caplog_structlog
        )
