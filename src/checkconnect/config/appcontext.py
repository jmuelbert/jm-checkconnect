"""
CheckConnect Application Context Module.

This module provides the core application context for CheckConnect, offering
a centralized way to manage shared resources like the logger, translation manager,
and application configuration. The `AppContext` class handles the
application state, ensuring all components can access common resources
consistently and, where applicable, in a thread-safe manner.

The `AppContext` serves as the central point of access for:
- **Application Logging**: Accessible via `get_module_logger()`.
- **Translation Management**: Accessible via `gettext()`.
- **Configuration Management**: Handled by the `config` attribute.

Main Components:
----------------
1.  **AppContext**:
    The primary class responsible for managing and providing access to shared
    resources. It's initialized with the application's configuration and
    language, providing methods to retrieve a logger and perform translations.

2.  **initialize_app_context()**:
    A helper function that streamlines the creation and initialization of
    an `AppContext` instance. It handles loading configurations from a TOML file
    and setting up language-specific translations.

Responsibilities:
-----------------
- Initialize and store shared application resources: logger, translation manager,
  and configuration settings.
- Provide unified access methods for logging and translations.
- Load configuration settings from external files (e.g., `config.toml`).
- Support internationalization through language-specific translations.

Usage Example:
--------------
```python
# Initialize application context with a config file and language
from pathlib import Path
from checkconnect.config.appcontext import initialize_app_context

# Assuming 'path/to/config.toml' exists
context = initialize_app_context(config_file=Path('path/to/config.toml'), language='en')

# Access logger and translator
logger = context.get_module_logger(__name__)
logger.info("Starting CheckConnect...")

translated_message = context.gettext("Hello, world!")
print(f"Translated: {translated_message}")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from checkconnect.config.logging_manager import LoggingManager
from checkconnect.config.settings_manager import SettingsManager
from checkconnect.config.translation_manager import TranslationManager

if TYPE_CHECKING:
    from pathlib import Path

    from structlog.stdlib import BoundLogger

log = structlog.get_logger(__name__)


@dataclass
class AppContext:
    """
    Manages shared application context, providing access to configuration,
    logging, and translation services.

    This class serves as a central hub for essential application components,
    ensuring consistent access to global resources across the application.

    Attributes
    ----------
    translator : TranslationManager
        Manages message translations for the UI and CLI.
    config : SettingsManager
        An instance of the settings manager for application configuration.
    """

    translator: TranslationManager
    config: SettingsManager

    def get_module_logger(self, name: str) -> BoundLogger:
        """
        Retrieves a `structlog` logger instance for a specific module.

        Parameters
        ----------
        name : str
            The name of the module for which to retrieve the logger (e.g., `__name__`).

        Returns
        -------
        structlog.stdlib.BoundLogger
            A bound logger instance for the specified module.
        """
        return structlog.get_logger(name)

    def gettext(self, message: str) -> str:
        """
        Translates a given message string using the active translation manager.

        Parameters
        ----------
        message : str
            The message string to be translated.

        Returns
        -------
        str
            The translated string.
        """
        return self.translator.gettext(message)

    @classmethod
    def create(
        cls,
        config: SettingsManager | None = None,
        language: str | None = None,
    ) -> AppContext:
        """
        Factory method to create and initialize an `AppContext` instance.

        This method loads application settings, configures the global logging
        system, and initializes the translation manager based on provided
        or default configuration and language settings.

        Parameters
        ----------
        config : SettingsManager | None, optional
            An optional pre-existing `SettingsManager` instance. If not provided,
            a new default `SettingsManager` will be created.
        language : str | None, optional
            An optional language code (e.g., 'en', 'de') for translations.
            If not provided, the default language configured by `TranslationManager`
            will be used.

        Returns
        -------
        AppContext
            A fully initialized `AppContext` instance.
        """
        config = config or SettingsManager()

        # The LoggingManager MUST be instantiated here to configure the global logging system
        # (i.e., structlog.configure() and setting up Python logger handlers).
        # However, the `logging_manager` instance doesn't strictly need to be stored in AppContext,
        # as it has fulfilled its purpose of _global configuration_.
        # If you intend to use the shutdown mechanism of the LoggingManager,
        # you could store the instance in AppContext and call the shutdown method
        # when the application exits (e.g., in an __exit__ method of AppContext).
        # For this specific logger name fix, though, it's not critical.
        _ = LoggingManager(config=config)  # The global logging is configured here

        translator = TranslationManager(language=language)

        return cls(translator=translator, config=config)


def initialize_app_context(
    config_file: Path | None = None,
    language: str | None = None,
) -> AppContext:
    """
    Initializes and returns a fully configured AppContext instance for the application.

    This function orchestrates the setup of the application's core context
    by loading settings from a configuration file and setting up language
    translations.

    Parameters
    ----------
    config_file : Path | None, optional
        The path to the TOML configuration file (e.g., `config.toml`).
        If `None`, default settings will be used.
    language : str | None, optional
        The language code for translations (e.g., 'en', 'de').
        If `None`, the system's default language or the default language
        of `TranslationManager` will be used.

    Returns
    -------
    AppContext
        A fully initialized `AppContext` instance, ready for use across the application.
    """
    config = SettingsManager(config_file=config_file)

    return AppContext.create(config=config, language=language)
