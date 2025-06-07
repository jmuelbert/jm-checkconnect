# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
CheckConnect Module.

This module provides a command-line interface (CLI) for managing network connectivity tests
and generating reports. It tests the connectivity to NTP servers and URLs, and allows the user
to generate HTML and PDF reports based on the results.

The module includes the following features:
- Running network tests for NTP servers and URLs.
- Generating HTML and PDF reports from the results of these tests.
- Using configuration settings from a TOML file.
- Supporting multiple languages for the application.

Classes:
- `CheckConnect`: A class that manages the NTP and URL tests and report generation.

Dependencies:
- `checkconnect.config.appcontext`: For managing application context and initialization.
- `checkconnect.core.ntp_checker`: For NTP server connectivity checks.
- `checkconnect.core.url_checker`: For URL connectivity checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

import structlog

from checkconnect.reports.report_manager import ReportManager

from .ntp_checker import NTPChecker, NTPCheckerConfig
from .url_checker import URLChecker, URLCheckerConfig

if TYPE_CHECKING:
    from checkconnect.config.appcontext import AppContext


# Definiere einen TypeVar für die Checker-Klasse, der auf NTPChecker oder URLChecker beschränkt ist
CheckerT = TypeVar("CheckerT", bound="NTPChecker | URLChecker")
# Definiere einen TypeVar für die Config-Klasse, der auf NTPCheckerConfig oder URLCheckerConfig beschränkt ist
ConfigT = TypeVar("ConfigT", bound="NTPCheckerConfig | URLCheckerConfig")

log = structlog.get_logger(__name__)

class CheckConnect:
    """
    Manage connectivity tests and report generation for NTP and URL checks.

    This class:
        - Runs network tests for NTP servers and URLs.
        - Generates reports based on the test results.

    Attributes
    ----------
        context (AppContext): Shared application context
        reports_dir (Path): Path for the reports or null if that config on settings

    """

    def __init__(self, context: AppContext) -> None:
        """
        Initialize the CheckConnect instance.

        Initializes NTP and URL checkers using shared context.
        Extracts relevant settings such as output directory.

        Args:
        ----
            context (AppContext): Shared application context with logger,
                translator, and configuration.

        """
        self.context = context
        self.logger = log
        self.translator = context.translator
        self.config = context.config
        self._ = context.gettext

        self.report_dir = self.config.get("reports", "directory", "reports")

        self.report_manager = ReportManager.from_context(context=self.context)

        # Initialize checkers
        self.ntp_checker = self._setup_checker(
            NTPChecker,
            NTPCheckerConfig,
            "ntp_servers",
        )

        self.url_checker = self._setup_checker(
            URLChecker,
            URLCheckerConfig,
            "urls"
        )

        # Results will be populated after `run()` is called
        self.ntp_results: list[str] = []
        self.url_results: list[str] = []

    def _setup_checker(
        self,
        checker_cls: type[CheckerT],
        config_cls: type[ConfigT],
        key: str,
    ) -> Any:
        """
        Help to set up a checker instance with its config.

        Args:
        ----
            checker_cls: The checker class (e.g., NTPChecker).
            config_cls: The config model class.
            key: The config key for 'ntp_servers' or 'urls'.

        Returns:
        -------
            An instance of the checker.

        """
        import sys  # Import sys for debugging prints

        print(f"\n--- DEBUG: Entering _setup_checker for key='{key}' ---", file=sys.stderr)
        print(f"DEBUG: self.config: {self.config}", file=sys.stderr)
        print(f"DEBUG: self.config.get_section: {self.config.get_section}", file=sys.stderr)

        network_config = self.config.get_section("network")
        print(f"DEBUG: network_config received from self.config.get_section('network'): {network_config}", file=sys.stderr)
        print(f"DEBUG: Type of network_config: {type(network_config)}", file=sys.stderr)
        print(f"DEBUG: network_config.get: {network_config.get}", file=sys.stderr)

        # Get values that will be passed to Pydantic config_cls
        ntp_or_url_list = network_config.get(key, [])
        timeout_value = network_config.get("timeout", 5)

        print(f"DEBUG: Value for '{key}': {ntp_or_url_list}, Type: {type(ntp_or_url_list)}", file=sys.stderr)
        print(f"DEBUG: Value for 'timeout': {timeout_value}, Type: {type(timeout_value)}", file=sys.stderr)

        print(f"DEBUG: _setup_checker: About to instantiate {config_cls.__name__}", file=sys.stderr)
        print(f"DEBUG: _setup_checker: Passing context to config_cls: {self.context}", file=sys.stderr)
        print(f"DEBUG: _setup_checker: Type of context: {type(self.context)}", file=sys.stderr)
        print(f"DEBUG: _setup_checker: Current self._ : {self._}", file=sys.stderr) # This is context.gettext mock
        print(f"DEBUG: _setup_checker: Checking for 'gettextsetup_checker' attribute on self: {hasattr(self, 'gettextsetup_checker')}", file=sys.stderr)
        print(f"DEBUG: _setup_checker: Checking for 'gettextsetup_checker' attribute on self.context: {hasattr(self.context, 'gettextsetup_checker')}", file=sys.stderr)
        print(f"DEBUG: _setup_checker: Checking for 'gettextsetup_checker' attribute on self._: {hasattr(self._, 'gettextsetup_checker')}", file=sys.stderr) # This is crucial


        try:
            config_dict = {
                key: ntp_or_url_list,
                "timeout": timeout_value,
                "context": self.context,
            }
            print(f"DEBUG: _setup_checker: Instantiating {config_cls.__name__} with: {config_dict}", file=sys.stderr)
            config = config_cls(**config_dict)
            print(f"DEBUG: _setup_checker: Successfully instantiated {config_cls.__name__}", file=sys.stderr)

            return checker_cls(config=config)

        except Exception as e:
            print(f"ERROR: _setup_checker: Exception during config_cls instantiation: {e}", file=sys.stderr)
            print(f"ERROR: _setup_checker: Exception type: {type(e)}", file=sys.stderr)

            # Re-raise to see the full traceback and confirm the source
            msg: str = self.context.gettext(f"Error configuring {checker_cls.__name__}")
            self.logger.exception(msg)
            raise

    def run_all_checks(self) -> None:
        """
        Run all connectivity tests (NTP and URLs).

        This method executes both the URL and NTP connectivity tests,
        logging progress and results. Exceptions are logged and re-raised.
        """
        self.logger.info(self.context.gettext("Starting all checks..."))

        self.run_url_checks()
        self.run_ntp_checks()

        self.logger.info(self.context.gettext("All checks completed successfully."))

    def run_url_checks(self) -> None:
        """Run URL checks only."""
        urls_text = self.config.get("network","urls")
        msg = self.context.gettext(f"Starting URL checks with {urls_text}")
        self.logger.info(msg)
        try:
            self.url_results = self.url_checker.run_url_checks()
            self.report_manager.save_url_results(self.url_results)
            self.logger.info(self.context.gettext("URL checks completed successfully."))
        except Exception:
            self.logger.exception(self.context.gettext("Error url checks."))
            raise

    def run_ntp_checks(self) -> None:
        """Run NTP checks only."""
        self.logger.info(self.context.gettext("Starting NTP checks..."))

        try:
            self.ntp_results = self.ntp_checker.run_ntp_checks()
            self.report_manager.save_ntp_results(self.ntp_results)
            self.logger.info(self.context.gettext("NTP checks completed successfully."))
        except Exception:
            self.logger.exception(self.context.gettext("Error during NTP checks."))
            raise
