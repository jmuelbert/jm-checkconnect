# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Unit tests for the URLChecker class.

This module contains comprehensive unit tests for the `URLChecker` class and
its associated configuration model `URLCheckerConfig`. It verifies the
correct initialization, validation, and execution of URL connectivity checks,
including handling various success and failure scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import requests
from pydantic import HttpUrl, ValidationError
from requests import RequestException

from checkconnect.core.url_checker import URLChecker, URLCheckerConfig

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest.logging import LogCaptureFixture  # Import LogCaptureFixture for caplog
    from pytest_mock import MockerFixture

    from checkconnect.config.appcontext import AppContext


@pytest.fixture
def valid_url_config(app_context_fixture: AppContext) -> URLCheckerConfig:
    """
    Fixture that returns a valid URLCheckerConfig instance.

    This fixture provides a pre-configured `URLCheckerConfig` object with
    example URL server addresses and a timeout, suitable for various tests.

    Args:
        app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.

    Returns:
        URLCheckerConfig: An instance of `NTPCheckerConfig` with valid settings.
    """
    return URLCheckerConfig(
        context=app_context_fixture,
        urls=["https://example.com", "https://google.com"],
        timeout=5,
    )


@pytest.mark.unit
class TestURLCheckerConfig:
    """
    Test cases for the `URLCheckerConfig` Pydantic model.

    This class verifies that `URLCheckerConfig` handles valid and invalid
    input correctly, ensuring proper data validation and error handling
    for URL server lists and timeout values.
    """

    @pytest.mark.unit
    def test_valid_config(self, valid_url_config: MagicMock) -> None:
        """
        Test the successful creation of a valid `URLCheckerConfig` instance.

        Verifies that the `urls` and `timeout` attributes are correctly
        assigned from the provided valid configuration.

        Args:
            valid_url_config (URLCheckerConfig): A pytest fixture providing a valid config.
        """
        checker = URLChecker(config=valid_url_config)

        assert isinstance(checker, URLChecker)
        assert len(checker.config.urls) == 2
        assert checker.config.urls == [HttpUrl("https://example.com"), HttpUrl("https://google.com")]
        assert checker.config.timeout == 5

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_direct_config_initialization(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test `URLCheckerConfig` instantiation when parameters are provided directly.

        Verifies that the configuration object is correctly created from explicit
        `urls` and `timeout` arguments along with the context.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        config = URLCheckerConfig(
            urls=["https://example.com", "https://google.com"],
            timeout=10,
            context=app_context_fixture,
        )
        assert isinstance(config, URLCheckerConfig)
        assert config.urls == [HttpUrl("https://example.com"), HttpUrl("https://google.com")]
        assert config.timeout == 10
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
            URLCheckerConfig(
                urls=["http://example.com"],
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
            URLCheckerConfig(
                urls=["http://example.com"],
                timeout="not-an-int",  # type: ignore[arg-type]
                context=app_context_fixture,
            )
        assert "Input should be a valid integer" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_invalid_url(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that an invalid URL server format raises a `ValidationError`.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            URLCheckerConfig(
                urls=["not-a-url"],
                timeout=5,
                context=app_context_fixture,
            )
        assert "urls" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_empty_urls_list(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that an empty list of URL servers raises a `ValidationError`.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            URLCheckerConfig(
                urls=[],
                timeout=5,
                context=app_context_fixture,
            )

        assert "Value error, At least one URL must be provided" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("test_input", "expected_error_substring"),
        [
            (
                {"urls": "not-a-list", "timeout": 5},
                "Input should be a valid list",
            ),
            (
                {"urls": ["http://example.com"], "timeout": "not-an-int"},
                "Input should be a valid integer",
            ),
            (
                {"urls": ["http://example.com"], "timeout": 0},
                "Timeout must be a positive integer",
            ),
            (
                {"urls": ["not-a-url"], "timeout": 5},
                "Input should be a valid URL",
            ),
        ],
    )
    @pytest.mark.unit
    def test_config_validation_errors(
        self,
        test_input: dict[str, Any],
        expected_error_substring: str,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test various validation error scenarios for `URLCheckerConfig`.

        This parameterized test ensures that `URLCheckerConfig` correctly
        raises `ValidationError` for invalid inputs, such as incorrect data types,
        out-of-range values, or malformed URL server addresses.

        Args:
            test_input (dict[str, Any]): A dictionary containing parameters to
                                        pass to `URLCheckerConfig`.
            expected_error_substring (str): A substring expected to be present
                                            in the `ValidationError` message.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        with pytest.raises(ValidationError) as exc_info:
            URLCheckerConfig(
                **test_input,
                context=app_context_fixture,
            )
        assert expected_error_substring in str(exc_info.value)


class TestURLChecker:
    """
    Test cases for the `URLChecker` class.

    This class contains tests for the core functionality of `URLChecker`,
    including successful URL requests, handling network errors, and
    processing multiple servers. It leverages mocks to isolate network
    interactions.
    """""

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_url_checker_integration(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test `URLChecker`'s integration with mocked `requests.get`.

        This test verifies that `URLChecker` can successfully perform an NTP check
        when `requests.get` is mocked to return a valid response.
        It also checks for appropriate log messages, including the `[mocked]` prefix.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        caplog.set_level(10)  # Set log level to DEBUG to capture INFO messages

        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mocker.patch("requests.get", return_value=mock_response)

        url_checker = URLChecker.from_params(
            context=app_context_fixture,
            urls = ["http://example.com"],
            timeout = 5,
        )

        results = url_checker.run_url_checks()

        assert isinstance(results, list)
        assert len(results) == 1
        assert all(isinstance(r, str) for r in results)

        assert "[mocked] Successfully connected to http://example.com/ with Status: 200" in results[0]

        # Check logger output for info messages with the '[mocked]' prefix
        assert any("[mocked] Checking URLs ..." in record.message for record in caplog.records)
        assert any("[mocked] Checking URL server: http://example.com/" in record.message for record in caplog.records)
        assert any("[mocked] Successfully connected to http://example.com/ with Status: 200" in record.message for record in caplog.records)

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_initialization(self, valid_url_config: URLCheckerConfig) -> None:
        """
        Test `URLChecker` initialization.

        Verifies that an `URLChecker` instance can be created and that its
        `config` attribute is correctly set.

        Args:
            valid_url_config (URLCheckerConfig): A pytest fixture providing a valid config.
        """
        checker = URLChecker(config=valid_url_config)

        assert isinstance(checker, URLChecker)
        assert checker.config == valid_url_config
        assert checker.config.context == valid_url_config.context

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_from_params(
        self,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test the `URLChecker.from_params` classmethod.

        Verifies that this convenience constructor correctly creates an
        `URLChecker` instance with the specified parameters, which are
        then wrapped into an `URLCheckerConfig`, and that the context is passed.

        Args:
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
        """
        checker = URLChecker.from_params(
            urls=["http://example.com"],
            timeout=5,
            context=app_context_fixture,
        )
        assert isinstance(checker, URLChecker)
        assert len(checker.config.urls) == 1
        assert checker.config.timeout == 5

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_run_url_checks_successful(
        self,
        mocker: MockFixture,
        valid_url_config: URLCheckerConfig,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test `run_url_checks` when all URL requests are successful.

        Mocks `requests.get` to always return a successful response
        and verifies that the results list contains success messages for all servers.
        Also checks for expected log messages including the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            valid_url_config (URLCheckerConfig): A pytest fixture providing a valid config.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        caplog.set_level(10)  # Set log level to DEBUG

        mock_response = mocker.Mock(spec=requests.Response)
        mock_response.status_code = 200
        mocker.patch("requests.get", return_value=mock_response)

        checker = URLChecker(config=valid_url_config)
        results = checker.run_url_checks()

        assert len(results) == 2
        assert "[mocked] Successfully connected to https://example.com/ with Status: 200" in results[0]
        assert "[mocked] Successfully connected to https://google.com/ with Status: 200" in results[1]

        # Check logger output
        assert any(
            "[mocked] Successfully connected to https://example.com/ with Status: 200" in record.message
            for record in caplog.records
        )
        assert any(
            "[mocked] Successfully connected to https://google.com/ with Status: 200" in record.message
            for record in caplog.records
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_run_url_checks_request_error(
        self,
        mocker: MockFixture,
        valid_url_config: URLCheckerConfig,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test `run_url_checks` when an `requests.get` occurs during a request.

        Mocks `requests.get` to raise an `RequestException` and verifies
        that the result reflects the error and an appropriate log message is emitted
        with the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            valid_url_config (URLCheckerConfig): A pytest fixture providing a valid config.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        caplog.set_level(10)  # Set log level to DEBUG

        mocker.patch(
            "requests.get",
            side_effect=RequestException("Connection failed"),
        )

        checker = URLChecker(config=valid_url_config)
        results = checker.run_url_checks()

        assert len(results) == 2
        assert "[mocked] Error by connection to https://example.com/: Connection failed" in results[0]
        assert "[mocked] Error by connection to https://google.com/: Connection failed" in results[1]

        # Check logger output for error messages
        assert any(
            "[mocked] Error by connection to https://example.com/" in record.message
            and "Connection failed" in record.message
            and record.levelname == "ERROR"  # Check log level
            for record in caplog.records
        )
        assert any(
            "[mocked] Error by connection to https://google.com/" in record.message
            and "Connection failed" in record.message
            and record.levelname == "ERROR"  # Check log level
            for record in caplog.records
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_url_checker_with_context(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        caplog: LogCaptureFixture
    ) -> None:
        """
        Test `URLChecker` functionality with a specific server configured via `from_params`.

        Verifies successful URL check and associated log messages including the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        caplog.set_level(10)  # Set log level to DEBUG

        mock_response = mocker.Mock(spec=requests.Response)
        mock_response.status_code = 200
        mocker.patch("requests.get", return_value=mock_response)

        url_checker = URLChecker.from_params(
            context=app_context_fixture,
            urls = ["https://example.com"],
            timeout = 5,
        )

        results = url_checker.run_url_checks()

        assert len(results) == 1
        assert "[mocked] Successfully connected to https://example.com/ with Status: 200" in results[0]


        # Check logger output
        assert any(
            "[mocked] Successfully connected to https://example.com/ with Status: 200"  in record.message for record in caplog.records
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_url_checker_with_site_not_found(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        caplog: LogCaptureFixture
    ) -> None:
        """
        Test `URLChecker`'s error handling for a site not found exception during URL request.

        Mocks `requests.get` to raise a ConnectionError `Exception` and
        verifies that the result indicates an error and an error log is generated
        with the `[mocked]` prefix and correct exception info.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        caplog.set_level(10)  # Set log level to DEBUG

        # Simulate a DNS resolution or connection error
        mocker.patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("Failed to establish a new connection"),
        )

        checker = URLChecker.from_params(
            context=app_context_fixture,
            urls=["https://www.that-server-does-not.exist"],
            timeout=2,
        )

        results = checker.run_url_checks()

        assert len(results) == 1
        assert "Error by connection to" in results[0] or "Failed to establish a new connection" in results[0]

        # Check logger output (the exception will be caught and logged by logger.exception)
        assert any(
            "[mocked] Error by connection to" in record.message
            and record.levelname == "ERROR"  # Or CRITICAL/EXCEPTION depending on structlog setup
            and "Failed to establish a new connection" in record.exc_info[1].args[0]  # Check original exception message in exc_info
            for record in caplog.records
        )

    @pytest.mark.unit
    @pytest.mark.parametrize("app_context_fixture", ["simple"], indirect=True)
    def test_multiple_urls(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test checking multiple URL servers with mixed results (success, failure, success).

        This test simulates a scenario where some URL server checks succeed and others fail,
        and verifies that `URLChecker` correctly records all outcomes and logs them
        appropriately with the `[mocked]` prefix.

        Args:
            mocker (MockerFixture): The `pytest-mock` fixture for creating mocks.
            app_context_fixture (AppContext): A pytest fixture providing an `AppContext`.
            caplog (LogCaptureFixture): The `pytest` fixture to capture log messages.
        """
        caplog.set_level(10)  # Set log level to DEBUG

        mock_success = mocker.Mock(spec=requests.Response)
        mock_success.status_code = 200
        mocker.patch(
            "requests.get",
            side_effect=[
                mock_success,
                RequestException("Failed"),
                mock_success,
            ],
        )

        config = URLCheckerConfig(
            urls=[
                "http://example1.com",
                "http://example2.com",
                "http://example3.com",
            ],
            timeout=5,
            context=app_context_fixture,
        )
        checker = URLChecker(config=config)
        results = checker.run_url_checks()

        assert len(results) == 3
        assert "Status: 200" in results[0]
        assert "Error by connection to" in results[1]
        assert "Status: 200" in results[2]

        # Check logger output for mixed results
        assert any(
            "[mocked] Checking URL server: http://example1.com/" in record.message for record in caplog.records
        )
        assert any(
            "[mocked] Successfully connected to http://example1.com/ with Status: 200" in record.message for record in caplog.records
        )
        assert any(
            "[mocked] Checking URL server: http://example2.com/" in record.message for record in caplog.records
        )
        assert any(
            "[mocked] Error by connection to http://example2.com/: Failed" in record.message
            and record.levelname == "ERROR"
            for record in caplog.records
        )
        assert any(
            "[mocked] Checking URL server: http://example3.com/" in record.message for record in caplog.records
        )
        assert any(
            "[mocked] Successfully connected to http://example3.com/ with Status: 200" in record.message for record in caplog.records
        )
