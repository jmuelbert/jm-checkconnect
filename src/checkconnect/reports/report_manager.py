# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
CheckConnect Report Manager Module.

This module manages the generation of summaries and handles the loading and saving of test result data files.
It provides functionalities to store NTP and URL test outcomes and to retrieve them for report generation.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import structlog
from platformdirs import user_data_dir

from checkconnect import __about__
from checkconnect.exceptions import (
    DirectoryCreationError,
    SummaryDataLoadError,
    SummaryDataSaveError,
    SummaryFormatError,
    SummaryUnknownDataError,
)

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

    from checkconnect.config.appcontext import AppContext
    from checkconnect.config.translation_manager import TranslationManager

log: BoundLogger = structlog.get_logger(__name__)


class OutputFormat(StrEnum):
    """Defines the supported output formats for summaries."""

    text = "text"
    markdown = "markdown"
    html = "html"


class ReportDataType(StrEnum):
    """Defines the types of report data that can be saved or loaded."""

    NTP = "ntp"
    URL = "url"


class ReportManager:
    """
    Manages the saving and loading of test results and generating summaries.

    This class handles the storage of results from NTP and URL connectivity tests,
    and provides methods to generate summaries in different formats (text, markdown, HTML).
    It also manages the output directory for reports and handles loading previous results.

    Attributes
    ----------
    context (AppContext): The application context containing configuration,
                          logger, and translation manager.
    logger (BoundLogger): The structured logger instance for logging events.
    translator (TranslationManager): The translation manager for i18n support.
    data_dir (Path): The directory where summary data files are stored.
    """

    _DATA_FILENAMES: Final[dict[ReportDataType, str]] = {
        ReportDataType.NTP: "ntp_results.json",
        ReportDataType.URL: "url_results.json",
    }

    context: AppContext
    logger: BoundLogger
    translator: TranslationManager
    data_dir: Path
    _: Any  # Placeholder for gettext function

    def __init__(
        self,
        context: AppContext,
        data_dir: Path,
    ) -> None:
        """
        Initialize the ReportManager instance.

        Args:
        ----
            context: The application context containing config, logger, and translator.
            data_dir: Directory to store the summary data.
        """
        self.context = context
        self.logger = log
        self.translator = context.translator
        self._ = self.translator.gettext
        self.data_dir = data_dir
        self._ensure_data_directory()  # Call it here after data_dir is set

    # --- Factory-Methods ---
    @classmethod
    def from_context(cls, context: AppContext) -> ReportManager:
        """
        Create a ReportManager instance from the application context.

        This factory method retrieves the data directory path from the application's
        configuration. If not found, it defaults to the system's user data directory.

        Args:
        ----
            context: The application context containing configuration, logger, and translator.

        Returns:
        -------
            A configured ReportManager instance.
        """
        # The default value for get should be the most robust and standard path
        default_data_path = str(user_data_dir(__about__.__app_name__, __about__.__app_org_id__))

        data_dir_str: str = context.settings.get("data", "directory", default_data_path)
        data_dir: Path = Path(data_dir_str)  # Convert to Path immediately

        # Log an info message if the default was used
        if data_dir_str == default_data_path:
            log.info(
                context.translator.translate(
                    f"Data directory not found in config or invalid. Using default: '{data_dir}'"
                )
            )
        else:
            log.info(context.translator.translate(f"Using data directory from config: '{data_dir}'"))

        instance = cls(context=context, data_dir=data_dir)
        return instance

    @classmethod
    def from_params(cls, context: AppContext, data_dir: Path) -> ReportManager:
        """
        Create a ReportManager instance with the specified data directory.

        This factory method allows direct specification of the data directory,
        overriding any configuration settings.

        Args:
        ----
            context: The application context containing config, logger, and translator.
            data_dir: The directory to store the data.

        Returns:
        -------
            A configured ReportManager instance.
        """
        # If data_dir can be None here, it should be handled:
        # Assuming data_dir from parameters will always be a Path or None
        if data_dir is None:
            data_dir = Path(user_data_dir(__about__.__app_name__, __about__.__app_org_id__))
            log.info(context.translator.translate(f"data_dir parameter was None. Using default: '{data_dir}'"))

        instance = cls(context=context, data_dir=data_dir)
        return instance

    def _ensure_data_directory(self) -> Path:
        """
        Ensure the specified data directory exists, creating it and parent directories if necessary.

        Returns:
        -------
            The path to the ensured data directory.

        Raises:
        ------
            DirectoryCreationError: If the directory cannot be created due to an OS error.
        """
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(self._(f"Ensured data directory exists: '{self.data_dir}'"))
        except OSError as e:
            translated_message = self._(f"Failed to create directory '{data_dir}'. Original error: {e}")
            self.logger.error(translated_message)
            raise DirectoryCreationError(translated_message, original_exception=e) from e
        else:
            return self.data_dir

    def _get_filepath(self, data_type: ReportDataType) -> Path:
        """
        Determine the full file path for a given report data type.

        Args:
        ----
            data_type: The type of report data (e.g., NTP, URL).

        Returns:
        -------
            The complete Path object for the data file.

        Raises:
        ------
            SummaryUnknownDataError: If an unknown `ReportDataType` is provided.
        """
        filename = self._DATA_FILENAMES.get(data_type)
        if filename is None:
            translated_message = self._(f"Unknown report data type: {data_type.value}. No filename configured.")
            raise SummaryUnknownDataError(translated_message)

        return self.data_dir / filename

    def _save_json(self, data_type: ReportDataType, data: list[str]) -> None:
        """
        Generic method to save JSON data based on the report data type.

        Args:
        ----
            data_type: The type of report data to save (e.g., NTP, URL).
            data: The list of strings to be saved as JSON.

        Raises:
        ------
            SummaryDataSaveError: If there's an issue saving the data (e.g., permissions, serialization error).
        """
        output_path = self._get_filepath(data_type)
        try:
            with output_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            msg = self._(f"Results for {data_type.value} saved to disk: {output_path}")
            self.logger.info(msg)
        except (OSError, TypeError, ValueError) as e:
            self.logger.exception(self._(f"Could not save {data_type.value} results due to an unexpected error."))
            translated_message = self._(f"Could not save {data_type.value} results to: {output_path}")
            raise SummaryDataSaveError(translated_message, original_exception=e) from e

    def _load_json(self, data_type: ReportDataType) -> list[str]:
        """
        Generic method to load JSON data based on the report data type.

        Args:
        ----
            data_type: The type of report data to load (e.g., NTP, URL).

        Returns:
        -------
            A list of strings loaded from the JSON file. Returns an empty list if the file
            does not exist.

        Raises:
        ------
            SummaryDataLoadError: If there's an issue loading or parsing the JSON data.
        """
        file_path = self._get_filepath(data_type)
        results: list[str] = []
        try:
            if file_path.exists():
                with file_path.open("r", encoding="utf-8") as f:
                    results = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.logger.exception(self._(f"Failed to load {data_type.value} results."))
            translated_message = self._(f"Failed to load {data_type.value} results from: {file_path}")
            raise SummaryDataLoadError(translated_message, original_exception=e) from e
        return results

    def save_ntp_results(self, data: list[str]) -> None:
        """
        Save the NTP test results to a JSON file.

        Args:
        ----
            data: A list of strings representing the NTP results.
        """
        self._save_json(ReportDataType.NTP, data)

    def load_ntp_results(self) -> list[str]:
        """
        Load the NTP test results from a JSON file.

        Returns:
        -------
            A list of strings representing the loaded NTP results.
        """
        return self._load_json(ReportDataType.NTP)

    def save_url_results(self, data: list[str]) -> None:
        """
        Save the URL test results to a JSON file.

        Args:
        ----
            data: A list of strings representing the URL results.
        """
        self._save_json(ReportDataType.URL, data)

    def load_url_results(self) -> list[str]:
        """
        Load the URL test results from a JSON file.

        Returns:
        -------
            A list of strings representing the loaded URL results.
        """
        return self._load_json(ReportDataType.URL)

    def load_previous_results(self) -> tuple[list[str], list[str]]:
        """
        Load previous NTP and URL results from disk.

        This method attempts to load NTP and URL results from their respective JSON files.
        If the files do not exist or cannot be read, it returns empty lists for those data types.

        Returns:
        -------
            A tuple containing two lists: NTP results and URL results.

        Raises:
        ------
            SummaryDataLoadError: If there's a problem loading the data from the files.
        """
        ntp_results: list[str] = self.load_ntp_results()
        print("[DEBUG] Loaded NTP results from file:", ntp_results)
        url_results: list[str] = self.load_url_results()
        print("[DEBUG] Loaded URL results from file:", url_results)

        self.logger.info(self._("Previous results loaded from disk."))
        return ntp_results, url_results

    def get_data_dir(self) -> Path:
        """
        Get the current data directory managed by the ReportManager.

        Returns:
        -------
            The Path object representing the data directory.
        """
        return self.data_dir

    def results_exists(self) -> bool:
        """
        Check if both NTP and URL result files exist in the data directory.

        Returns:
        -------
            True if both result files exist, False otherwise.
        """
        ntp_file = self._get_filepath(ReportDataType.NTP)
        url_file = self._get_filepath(ReportDataType.URL)

        return ntp_file.exists() and url_file.exists()

    def get_summary(
        self,
        ntp_results: list[str],
        url_results: list[str],
        summary_format: OutputFormat,
    ) -> str:
        """
        Generate a summary of the results in the specified format.

        This method compiles the NTP and URL results into a human-readable summary
        formatted as plain text, Markdown, or HTML.

        Args:
        ----
            ntp_results: List of NTP check results.
            url_results: List of URL check results.
            summary_format: The desired output format for the summary (text, markdown, or html).

        Returns:
        -------
            The generated summary as a string in the specified format.

        Raises:
        ------
            SummaryFormatError: If an invalid `OutputFormat` is specified.
        """
        if summary_format not in {OutputFormat.text, OutputFormat.markdown, OutputFormat.html}:
            translated_message = self._(
                f"Invalid format specified. Use 'text', 'markdown', or 'html' instead of {summary_format}."
            )
            raise SummaryFormatError(translated_message)

        url_section = self._format_section(
            self._("URL Check Results"),
            url_results,
            summary_format,
        )
        ntp_section = self._format_section(
            self._("NTP Check Results"),
            ntp_results,
            summary_format,
        )

        if summary_format == OutputFormat.html:
            return f"<html><body>{url_section}<br><br>{ntp_section}</body></html>"
        return f"{url_section}\n\n{ntp_section}"

    def _format_section(self, title: str, lines: list[str], summary_format: OutputFormat) -> str:
        """
        Format a section of the report based on the specified format.

        This helper method applies specific formatting (e.g., Markdown headings, HTML lists)
        to a given section title and its content lines.

        Args:
        ----
            title: The title of the section.
            lines: The lines of content for the section.
            summary_format: The format for the section (text, markdown, or html).

        Returns:
        -------
            The formatted section as a string.
        """
        if summary_format == OutputFormat.markdown:
            body = "\n".join(f"- {line}" for line in lines or [])
            return f"## {title}\n{body}"
        if summary_format == OutputFormat.html:
            body = "<ul>" + "".join(f"<li>{line}</li>" for line in lines or []) + "</ul>"
            return f"<h2>{title}</h2>{body}"

        body = "\n".join(lines or [])
        return f"{title}:\n{body}"
