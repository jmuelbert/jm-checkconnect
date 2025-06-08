# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""Check the HTTP status of URLs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests
import structlog
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator, model_validator

from checkconnect.config.appcontext import AppContext  # noqa: TCH001

if TYPE_CHECKING:
    from collections.abc import Mapping

log = structlog.get_logger(__name__)


class URLCheckerConfig(BaseModel):
    """
    Pydantic model for validating URLChecker configuration.

    This model includes fields for URL servers, timeout, and application context.
    It also includes validators for the URL server list and timeout value.

    Attributes
    ----------
    urls list[HttpUrl]:
        List of URL server hostnames.
    timeout (int):
        Timeout for each NTP request in seconds.
    context (AppContext):
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
        """Ensure the list of URLs is not empty."""
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
    config (NTPCheckerConfig):
        The configuration object holding parameters for the checker.
    logger (structlog.stdlib.BoundLogger):
        Logger instance for logging messages.
    translator (Any):
        Translator instance from the context, used for localization of messages.
    _ (Callable[[str], str]):
        A shortcut to the translation function `translator.gettext`.
    results (list[str]):
        A list to store the results of each NTP check.

    """

    def __init__(self, config: URLCheckerConfig) -> None:
        """
        Initialize the URLChecker with a validated configuration.

        Args:
        ----
            config: A URLCheckerConfig instance containing the configuration parameters.

        Raises:
            ValueError: If `config.context` is None or if no NTP servers are
                        provided in the configuration.
        """
        if not config.context:
            msg = config.context.translator.gettext("URLCheckerConfig.context must not be None")
            raise ValueError(msg)
        self.config: URLCheckerConfig = config
        self.logger = log
        self.translator = config.context.translator
        self._ = self.translator.gettext

        self.results: list[str] = []

        if not self.config.urls:
            msg = self._("No URL servers provided in configuration.")
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
            urls (list[str]):
                The list of URL servers to check.
            timeout (int):
                The timeout in seconds to wait for a response from each NTP server.

        Returns:
            URLChecker: A configured URLChecker instance.
        """

        config = URLCheckerConfig(context=context, urls=urls, timeout=timeout)
        return cls(config=config)

    def run_url_checks(self) -> list[str]:
        """
        Check the HTTP status of URLs.

        This method iterates through the list of URLs, sends an HTTP GET
        request to each URL, and logs the status code.  If a request
        exception occurs, it logs the error message.
        Any errors during the request are caught and logged.

        Returns
        -------
            A list of strings, where each string represents the result of checking a URL.
            The result can be either the status code of the URL or an error message
            if the URL check failed.

        """
        self.logger.info(self._("Checking URLs ..."))

        for url in self.config.urls:
            msg: str = self._(f"Checking URL server: {url}")
            self.logger.debug(msg)
            try:
                response: requests.Response = requests.get(
                    str(url),
                    timeout=self.config.timeout,
                )
                result: str = self._(f"Successfully connected to {url} with Status: {response.status_code}")
                self.logger.debug(result)
                self.results.append(result)
            except requests.RequestException as e:
                error_message: str = self._(f"Error by connection to {url}: {e}")
                self.logger.exception(error_message)
                self.results.append(error_message)
            except Exception as e:  # Another specific exception should be managed.
                error_message = self._(f"An unexpected error occurred while checking {url}: {e}")
                self.logger.exception(error_message)
                self.results.append(error_message)

        self.logger.info(self._("All URL servers checked."))
        return self.results


URLCheckerConfig.model_rebuild()
