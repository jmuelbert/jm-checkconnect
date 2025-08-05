# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
CheckConnect Module.

This module provides the core logic for managing network connectivity tests
and generating reports. It includes functionalities to test connectivity
to NTP servers and URLs, and to produce reports in various formats based
on the test outcomes.

The module integrates with the application's configuration, logging, and
translation managers to ensure a consistent and robust testing environment.

Classes:
- `CheckConnect`: The main class orchestrating NTP and URL checks, and report generation.

Dependencies:
- `checkconnect.config.appcontext`: Manages the application-wide context.
- `checkconnect.core.ntp_checker`: Handles NTP server connectivity tests.
- `checkconnect.core.url_checker`: Handles URL connectivity tests.
- `checkconnect.reports.report_manager`: Manages saving and loading test results, and generating summaries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import structlog

from checkconnect.core.ntp_checker import NTPChecker, NTPCheckerConfig
from checkconnect.core.url_checker import URLChecker, URLCheckerConfig
from checkconnect.reports.report_manager import ReportManager

if TYPE_CHECKING:
    from collections.abc import Callable

    from checkconnect.config.appcontext import AppContext

# Define a TypeVar for checker classes, constrained to NTPChecker or URLChecker.
CheckerT = TypeVar("CheckerT", bound="NTPChecker | URLChecker")
# Define a TypeVar for configuration classes, constrained to NTPCheckerConfig or URLCheckerConfig.
ConfigT = TypeVar("ConfigT", bound="NTPCheckerConfig | URLCheckerConfig")

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)


class CheckConnect:
    """
    Manages network connectivity tests for NTP servers and URLs, and orchestrates report generation.

    This class serves as the central component for executing connectivity checks
    and coordinating with various sub-components (e.g., NTPChecker, URLChecker,
    ReportManager) to perform its functions. It initializes these components
    based on the provided application context and handles the full lifecycle
    of the connectivity tests.

    Attributes
    ----------
    context (AppContext): The shared application context containing configuration,
                          logger, and translation manager.
    logger (BoundLogger): The structured logger instance for logging events specific
                          to the CheckConnect operations.
    translator (TranslationManager): The translation manager for internationalization support.
    config (SettingsManager): The settings manager providing access to application configuration.
    _translate_func (Callable): A shortcut for the `gettext` translation function.
    report_dir (str): The configured directory path for storing generated reports.
    report_manager (ReportManager): An instance of `ReportManager` for handling test result data.
    ntp_checker (NTPChecker): An instance of `NTPChecker` configured for NTP connectivity tests.
    url_checker (URLChecker): An instance of `URLChecker` configured for URL connectivity tests.
    ntp_results (list[str]): A list to store the results of NTP checks after execution.
    url_results (list[str]): A list to store the results of URL checks after execution.
    """

    # Type definition for the translation function
    _translate_func: Callable[[str], str]

    def __init__(self, context: AppContext) -> None:
        """
        Initialize the CheckConnect instance.

        This constructor initializes the `CheckConnect` object by setting up
        its core dependencies, including the logger, translator, configuration,
        and instances of `ReportManager`, `NTPChecker`, and `URLChecker`.
        Checker instances are dynamically configured based on application settings.

        Args:
        ----
            context (AppContext): The shared application context, providing access
                                  to logging, translation, and configuration settings.
        """
        self.context = context
        self.translator = context.translator
        self.config = context.settings
        self._translate_func = context.translator.gettext

        self.report_dir = self.config.get("reports", "directory", "reports")

        self.report_manager = ReportManager.from_context(context=self.context)

        # Initialize checkers dynamically based on their respective configurations
        self.ntp_checker = self._setup_checker(
            NTPChecker,
            NTPCheckerConfig,
            "ntp_servers",
        )

        self.url_checker = self._setup_checker(URLChecker, URLCheckerConfig, "urls")

        # Initialize result storage; these will be populated after `run_all_checks()`
        self._ntp_results: list[str] = []
        self._url_results: list[str] = []

    def _setup_checker(
        self,
        checker_cls: type[CheckerT],
        config_cls: type[ConfigT],
        key: str,
    ) -> CheckerT:
        """
        Help to set up and configure a checker instance.

        This method retrieves network configuration details from the application context,
        constructs a configuration object using the provided `config_cls`, and then
        instantiates the `checker_cls` with this configuration. It handles potential
        configuration errors by logging them and re-raising the exception.

        Args:
        ----
            checker_cls: The class of the checker to instantiate (e.g., `NTPChecker`, `URLChecker`).
            config_cls: The Pydantic configuration model class for the checker (e.g., `NTPCheckerConfig`).
            key: The configuration key (e.g., "ntp_servers" or "urls") to retrieve the list
                 of items to be checked.

        Returns:
        -------
            An instantiated and configured checker object.

        Raises:
        ------
            Exception: If an error occurs during the configuration or instantiation
                       of the checker, typically due to invalid settings.

        """
        network_config = self.config.get_section("network")

        # Get values that will be passed to Pydantic config_cls
        ntp_or_url_list = network_config.get(key, [])

        timeout_value = network_config.get("timeout", 5)

        try:
            config_dict = {
                key: ntp_or_url_list,
                "timeout": timeout_value,
                "context": self.context,
            }
            config = config_cls(**config_dict)

            return checker_cls(config=config)

        except Exception as e:
            msg: str = self._translate_func("Error configuring {}")
            log.exception(msg, name=checker_cls.__name__, exc_info=e)
            raise

    @property
    def ntp_results(self) -> list[str]:
        """Get the results of the NTP checks."""
        return self._ntp_results

    @ntp_results.setter
    def ntp_results(self, ntp_data: list[str]) -> None:
        """Set the results of the NTP checks."""
        self._ntp_results = ntp_data

    @property
    def url_results(self) -> list[str]:
        """Get the results of the URL checks."""
        return self._url_results

    @url_results.setter
    def url_results(self, url_data: list[str]) -> None:
        """Set the results of the NTP checks."""
        self._url_results = url_data

    def run_all_checks(self) -> None:
        """
        Execute all configured network connectivity tests (NTP and URLs).

        This method orchestrates the execution of both URL and NTP connectivity
        tests. It logs the start and completion of the checks, and handles
        any exceptions that occur during their execution by logging them and
        re-raising.
        """
        log.info(self._translate_func("Starting all checks..."))
        try:
            self.run_url_checks()
            self.run_ntp_checks()
        except Exception as e:
            log.exception("Error running all checks", exc_info=e)
            raise

        log.info(self._translate_func("All checks completed successfully."))

    def run_url_checks(self) -> None:
        """
        Run only the URL connectivity checks.

        This method invokes the `run_url_checks` method of the `url_checker` instance,
        stores the results, and saves them using the `report_manager`.
        It logs the process and handles potential exceptions during the checks.

        Raises:
        ------
            Exception: If an error occurs during the URL connectivity checks.
        """
        urls_text = self.config.get("network", "urls")
        msg = self._translate_func("Starting URL checks. with")
        log.info(msg, urls_text=urls_text)
        try:
            self._url_results = self.url_checker.run_url_checks()
            self.report_manager.save_url_results(self._url_results)
            log.info(self._translate_func("URL checks completed successfully."))
        except Exception as e:
            log.exception(self._translate_func("Error url checks."), exc_info=e)
            raise

    def run_ntp_checks(self) -> None:
        """
        Run only the NTP connectivity checks.

        This method invokes the `run_ntp_checks` method of the `ntp_checker` instance,
        stores the results, and saves them using the `report_manager`.
        It logs the process and handles potential exceptions during the checks.

        Raises:
        ------
            Exception: If an error occurs during the NTP connectivity checks.
        """
        log.info(self._translate_func("Starting NTP checks..."))

        try:
            self._ntp_results = self.ntp_checker.run_ntp_checks()
            self.report_manager.save_ntp_results(self._ntp_results)
            log.info(self._translate_func("NTP checks completed successfully."))
        except Exception as e:
            log.exception(self._translate_func("Error during NTP checks."), exc_info=e  )
            raise
