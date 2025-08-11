# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Check time synchronization with NTP servers.

This module defines the NTPChecker class and configuration for verifying
NTP server connectivity and time synchronization using the `ntplib` library.
It validates input configurations, performs NTP requests, and logs results.
"""

from __future__ import annotations

import ipaddress
import re
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

import ntplib
import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from checkconnect.config.appcontext import AppContext  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)

# Regular expression for DNS-compliant hostnames
HOSTNAME_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Z\d-]{1,63}(?<!-)(?:\.(?!-)[A-Z\d-]{1,63}(?<!-))+\.?$",
    re.IGNORECASE,
)

# Annotated type for a list of NTP servers with at least one entry
NTPList = Annotated[list[str], Field(min_length=1)]


class NTPCheckerConfig(BaseModel):
    """
    Pydantic model for validating NTPChecker configuration.

    This model includes fields for NTP servers, timeout, and application context.
    It also includes validators for the NTP server list and timeout value.

    Attributes
    ----------
    ntp_servers (NTPList):
        List of NTP server hostnames or IP addresses.
    timeout (int):
        Timeout for each NTP request in seconds.
    context (AppContext):
        Application context for logging and other services.

    """

    ntp_servers: NTPList
    timeout: int
    context: AppContext

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
            msg = "context must be provided to NTPCheckerConfig"
            raise ValueError(msg)
        return values

    @field_validator("ntp_servers", mode="after")
    @classmethod
    def validate_ntp_servers(cls, v: list[str]) -> list[str]:
        """
        Validate the list of NTP servers.

        This method checks if each entry in the list is a valid IP address or
        a DNS-compliant hostname. If any entry is invalid, a ValueError is raised.

        Args:
            v (list[str]): List of NTP server hostnames or IP addresses.

        Returns:
            list[str]: The validated list of NTP servers.

        Raises:
            ValueError: If any NTP server entry is not a valid IP address or hostname.
        """

        def is_valid(entry: str) -> bool:
            """
            Check if the entry is a valid IP address or DNS-compliant hostname.

            Args:
                entry (str): The entry to check.

            Returns:
                bool: True if the entry is valid, False otherwise.
            """
            try:
                ipaddress.ip_address(entry)
            except ValueError:
                return bool(HOSTNAME_PATTERN.match(entry))
            else:
                return True

        invalid = [host for host in v if not is_valid(host)]
        if invalid:
            msg = f"Invalid NTP servers: {invalid}"
            raise ValueError(msg)
        return v

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


class NTPChecker:
    """
    NTPChecker performs NTP server checks based on configuration.

    This class initializes with an `NTPCheckerConfig` object and provides methods
    to perform NTP synchronization checks against the configured servers. It logs
    the results, including time differences and any errors encountered.

    Attributes
    ----------
    config (NTPCheckerConfig):
        The configuration object holding parameters for the checker.
    logger (structlog.stdlib.BoundLogger):
        Logger instance for logging messages.
    translator (Any):
        Translator instance from the context, used for localization of messages.
    _.translate_func (Callable[[str], str]):
        A shortcut to the translation function `translator.gettext`.
    results (list[str]):
        A list to store the results of each NTP check.

    """

    # Type definition for the translation function
    _translate_func: Callable[[str], str]

    def __init__(self, config: NTPCheckerConfig) -> None:
        """
        Initialize the NTPChecker with a configuration.

        Args:
            config (NTPCheckerConfig):
                An `NTPCheckerConfig` instance containing the configuration parameters.

        Raises:
            ValueError: If `config.context` is None or if no NTP servers are
                        provided in the configuration.
        """
        if not config.context:
            msg = config.context.translator.gettext("NTPCheckerConfig.context must not be None")
            raise ValueError(msg)
        self.config: NTPCheckerConfig = config
        self.translator = config.context.translator
        self._translate_func = config.context.translator.gettext

        self.results: list[str] = []

        if not self.config.ntp_servers:
            msg = self._translate_func("No NTP servers provided in configuration.")
            raise ValueError(msg)

    @classmethod
    def from_context(cls, context: AppContext) -> NTPChecker:
        """
        Create an NTPChecker instance from an application context with default parameters.

        This class method constructs an `NTPCheckerConfig` with an empty list
        of NTP servers and a default timeout of 5 seconds, then initializes
        an `NTPChecker` instance.

        Args:
            context (AppContext):
                The application context containing logger and translator.

        Returns:
            NTPChecker: A configured NTPChecker instance.
        """
        config = NTPCheckerConfig(
            ntp_servers=[],
            timeout=5,
            context=context,
        )
        return cls(config=config)

    @classmethod
    def from_params(cls, context: AppContext, ntp_servers: list[str], timeout: int) -> NTPChecker:
        """
        Create an NTPChecker from an application context and specific parameters.

        This class method constructs an `NTPCheckerConfig` using the provided
        `context`, `ntp_servers`, and `timeout`, then initializes an `NTPChecker` instance.

        Args:
            context (AppContext):
                The application context containing config, logger, and translator.
            ntp_servers (list[str]):
                The list of NTP servers to check.
            timeout (int):
                The timeout in seconds to wait for a response from each NTP server.

        Returns:
            NTPChecker: A configured NTPChecker instance.
        """
        config = NTPCheckerConfig(context=context, ntp_servers=ntp_servers, timeout=timeout)
        return cls(config=config)

    def run_ntp_checks(self) -> list[str]:
        """
        Perform NTP synchronization checks for each configured server.

        This method iterates through the list of NTP servers in the configuration,
        sends an NTP request to each, calculates the time difference between the
        NTP server's time and the local system's time, and logs the outcome.
        Any errors during the request are caught and logged.

        Returns:
            list[str]:
                A list of strings summarizing the synchronization result
                or error for each NTP server.
        """
        log.info(self._translate_func("Checking NTP servers..."))

        for server in self.config.ntp_servers:
            log.debug(self._translate_func("Checking NTP server"), server=server)
            try:
                client = ntplib.NTPClient()
                response = client.request(
                    server,
                    version=3,
                    timeout=self.config.timeout,
                )
                # Convert NTP time to a timezone-aware UTC datetime
                ntp_time = datetime.fromtimestamp(response.tx_time, tz=UTC)
                # Get current local time as a timezone-aware UTC datetime
                local_time = datetime.now(tz=UTC)

                difference = (ntp_time - local_time).total_seconds()

                result: str = self._translate_func(
                    f"Successfully retrieved time from {server} - Time: {time.ctime(response.tx_time)} - Difference: {difference:.2f}s",
                )
                self.results.append(result)
                log.debug(
                    self._translate_func("Successfully retrieved time from server"),
                    server=server,
                    time=time.ctime(response.tx_time),
                    difference=difference,
                )

            except ntplib.NTPException as e:
                error_message = self._translate_func(
                    f"Error retrieving time from NTP server {server}: {e}",
                )
                self.results.append(error_message)
                log.exception(self._translate_func("Error retrieving time from NTP server"), server=server, exc_info=e)

            except Exception as e:
                error_message = self._translate_func(
                    f"An unexpected error occurred while checking NTP server {server}: {e}"
                )
                self.results.append(error_message)
                log.exception(
                    self._translate_func("An unexpected error occurred while checking NTP server"),
                    server=server,
                    exc_info=e,
                )

        log.info(self._translate_func("All NTP servers checked."))
        return self.results


NTPCheckerConfig.model_rebuild()
