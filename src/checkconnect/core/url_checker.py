# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Check the HTTP status of URLs.

This module defines the URLChecker class and configuration for verifying
URL (Web) server connectivity and time synchronization using the `requests` library.
It validates input configurations, performs URL requests, and logs results.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests
import structlog
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator, model_validator

from checkconnect.config.appcontext import AppContext  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)


class URLCheckerConfig(BaseModel):
    """
    Pydantic model for validating URLChecker configuration.

    This model includes fields for URL servers, timeout, and application context.
    It also includes validators for the URL server list and timeout value.

    Attributes
    ----------
    urls : list[HttpUrl]
        List of URL server hostnames.
    timeout : int
        Timeout for each HTTP request in seconds.
    context : AppContext
        Application context for logging and other services.

    """

    urls: list[HttpUrl]
    timeout: int
    context: AppContext

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )  # Allow TranslationManager and logger

    @model_validator(mode="before")
    @classmethod
    def check_context_present(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Validate that the application context is provided.

        Args:
            values (Mapping[str, Any]): The dictionary of field values being validated.

        Returns:
            Mapping[str, Any]: The validated dictionary of field values.

        Raises:
            ValueError: If 'context' is not provided in the values.
        """
        context = values.get("context")
        if context is None:
            msg = "context must be provided to URLCheckerConfig."
            raise ValueError(msg)
        return values

    @field_validator("urls")
    @classmethod
    def urls_must_not_be_empty(cls, urls: list[HttpUrl]) -> list[HttpUrl]:
        """
        Validate that the list of URLs is not empty.

        Args:
            urls (list[HttpUrl]): The list of URLs to validate.

        Returns:
            list[HttpUrl]: The validated list of URLs.

        Raises:
            ValueError: If the list of URLs is empty.
        """
        if not urls:
            msg: str = "At least one URL must be provided"
            raise ValueError(msg)
        return urls

    @field_validator("timeout")
    @classmethod
    def timeout_must_be_positive(cls, value: int) -> int:
        """
        Validate that the timeout is a positive integer.

        This method checks if the timeout value is greater than zero.
        If not, a ValueError is raised.

        Args:
            value (int): The timeout value to validate.

        Returns:
            int: The validated timeout value.

        Raises:
            ValueError: If the timeout value is not a positive integer.
        """
        if value <= 0:
            msg = "Timeout must be a positive integer"
            raise ValueError(msg)
        return value


class URLChecker:
    """
    Check the HTTP status of URLs.

    This class provides functionality to check the HTTP status of a list of URLs,
    using the `requests` library to send HTTP GET requests and handle potential
    exceptions.

    Attributes
    ----------
    config : URLCheckerConfig
        The configuration object holding parameters for the checker.
    logger : structlog.stdlib.BoundLogger
        Logger instance for logging messages.
    translator : Any
        Translator instance from the context, used for localization of messages.
    __translate_func (Callable[[str], str]):
        A shortcut to the translation function `translator.gettext`.
    results : list[str]
        A list to store the results of each URL check.

    """

    # Type definition for the translation function
    _translate_func: Callable[[str], str]

    def __init__(self, config: URLCheckerConfig) -> None:
        """
        Initialize the URLChecker with a validated configuration.

        Args:
        ----
            config (URLCheckerConfig): A URLCheckerConfig instance containing the
                                       configuration parameters.

        Raises:
            ValueError: If `config.context` is None or if no URLs are
                        provided in the configuration.
        """
        if not config.context:
            msg = config.context.translator.gettext("URLCheckerConfig.context must not be None")
            raise ValueError(msg)
        self.config: URLCheckerConfig = config
        self.translator = config.context.translator
        self._translate_func = config.context.translator.gettext

        self.results: list[str] = []

        if not self.config.urls:
            msg = self._translate_func("No URL servers provided in configuration.")
            raise ValueError(msg)

    @classmethod
    def from_context(cls, context: AppContext) -> URLChecker:
        """
        Create an URLChecker instance from an application context with default parameters.

        This class method constructs an `URLCheckerConfig` with an empty list
        of URL servers and a default timeout of 5 seconds, then initializes
        an `URLChecker` instance.

        Parameters
        ----------
        context : AppContext
            The application context containing logger and translator.

        Returns
        -------
        URLChecker
            A configured URLChecker instance.

        """
        config = URLCheckerConfig(
            urls=[],
            timeout=5,
            context=context,
        )
        return cls(config=config)

    @classmethod
    def from_params(cls, context: AppContext, urls: list[HttpUrl], timeout: int) -> URLChecker:
        """
        Create an URLChecker from an application context and specific parameters.

        This class method constructs an `URLCheckerConfig` using the provided
        `context`, `urls`, and `timeout`, then initializes an `URLChecker` instance.

        Args:
            context (AppContext):
                The application context containing config, logger, and translator.
            urls (list[HttpUrl]):
                The list of URL servers to check.
            timeout (int):
                The timeout in seconds to wait for a response from each URL.

        Returns:
            URLChecker: A configured URLChecker instance.
        """
        config = URLCheckerConfig(context=context, urls=urls, timeout=timeout)
        return cls(config=config)

    def run_url_checks(self) -> list[str]:
        """
        Check the HTTP status of URLs.

        This method iterates through the list of URLs, sends an HTTP GET
        request to each URL, and logs the status code. If a request
        exception occurs, it logs the error message.
        Any errors during the request are caught and logged.

        Returns
        -------
            list[str]: A list of strings, where each string represents the result of checking a URL.
                       The result can be either the status code of the URL or an error message
                       if the URL check failed.

        """
        log.info(self._translate_func("Checking URLs ..."))

        for url in self.config.urls:
            msg: str = self._translate_func("Checking URL server.")
            log.debug(msg, server=str(url))
            try:
                response: requests.Response = requests.get(
                    str(url),
                    timeout=self.config.timeout,
                )

                log.debug(
                    self._translate_func("Successfully connected to Web-Server"),
                    server=str(url),
                    status_code=response.status_code,
                )
                self.results.append(
                    self._translate_func(f"Successfully connected to {url} with Status: {response.status_code}")
                )
            except requests.RequestException as e:
                log.exception(self._translate_func("Error by connection"), server=str(url), exc_info=e)
                self.results.append(self._translate_func(f"Error by connection to {url}: {e}"))
            except Exception as e:  # Another specific exception should be managed.
                log.exception(
                    self._translate_func("An unexpected error occurred while checking Web-Server"),
                    server=url,
                    exc_info=e,
                )
                self.results.append(
                    self._translate_func(
                        f"An unexpected error occurred while checking Web-Server: {url} with error: {e}"
                    )
                )

        log.info(self._translate_func("All Web-Servers checked."))
        return self.results


URLCheckerConfig.model_rebuild()
