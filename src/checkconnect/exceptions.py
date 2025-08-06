# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

from pathlib import Path


class BaseReportError(Exception):
    """Basis-Exception für alle Berichts-bezogenen Fehler."""


# CLI


class ExitExceptionError(BaseReportError):
    """Exception for CLI issues."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


# LoggingManager
# --- Custom Exceptions ---
class LoggerConfigurationError(BaseReportError):
    """Base exception for logger configuration errors."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class InvalidLogLevelError(BaseReportError):
    """Raised when an invalid log level string is found in the config."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class LogDirectoryError(BaseReportError):
    """Raised when creating the log directory fails."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class LogHandlerError(BaseReportError):
    """Raised when creating a log file handler fails."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


# Settings-ReportManager
class SettingsConfigurationError(Exception):
    """Base exception for logger configuration errors."""

    def __init__(self, path: Path) -> None:
        super().__init__("Invalid TOML syntax in configuration file")


class SettingsWriteConfigurationError(Exception):
    """Base exception for logger configuration errors."""

    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class ConfigFileNotFoundError(SettingsConfigurationError, FileNotFoundError):
    """Raised when the configuration file is not found."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Configuration file not found")


# class InvalidConfigFileError(SettingsConfigurationError, ValueError):
#     """Raised when the configuration file is invalid (e.g., bad TOML)."""

#     def __init__(self, number: int) -> None:
#         super().__init__(f"{number} is negative")


# Reports
class DirectoryCreationError(BaseReportError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


# ReportManager
class SummaryDataLoadError(BaseReportError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class SummaryDataSaveError(BaseReportError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class SummaryUnknownDataError(BaseReportError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class SummaryFormatError(BaseReportError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception


class SummaryValueError(BaseReportError):
    def __init__(self, message: str):
        super().__init__(message)


# Report Generator


class ReportsMissingDataError(BaseReportError):
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        if original_exception:
            self.__cause__ = original_exception
