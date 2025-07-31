# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
SettingsManager module.

For loading, accessing, and persisting configuration
settings in the CheckConnect application.

This module defines the `SettingsManager` class, which handles:
- Loading configuration from predefined TOML files.
- Falling back to default settings if no valid file is found.
- Persisting updated configurations to disk.
- Supporting both system-wide and user-specific config locations.

The configuration includes sections for logging, file handling, output
directories, network timeouts, and data file paths.

This implementation supports Python 3.11+ (using tomllib), and falls back
to tomli/toml for compatibility in earlier Python versions.
"""

from __future__ import annotations

import copy
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any, ClassVar, TypeVar, Optional

import platformdirs
import structlog
import tomli_w

from checkconnect.__about__ import __app_config_name__, __app_name__
from checkconnect.exceptions import ConfigFileNotFoundError, SettingsConfigurationError, SettingsWriteConfigurationError

# Global logger for main.py (will be reconfigured by LoggingManagerSingleton)
log: structlog.stdlib.BoundLogger
log = structlog.get_logger(__name__)

T = TypeVar("T")


class SettingsManager:
    """
    Manage configuration loading, saving, and access for CheckConnect.

    This class attempts to load configuration data from a list of known
    locations, falling back to defaults if none are found. It also supports
    writing default or updated settings to the first writable location.

    The configuration is expected to be in TOML format and structured into
    sections such as "logger", "file_handler", "Files", etc.

    Attributes
    ----------
    DEFAULT_SETTINGS_LOCATIONS (ClassVar[list[Path]]):
        An ordered list of file paths to check for configuration files.
    DEFAULT_CONFIG (ClassVar[dict[str, dict[str, Any]]]):
        The fallback configuration used if no valid file is found.
    config (dict[str, dict[str, Any]]):
        The active configuration loaded at runtime.
    """

    _internal_errors: list[str]

    APP_NAME: ClassVar[str] = __app_name__.lower()
    CONF_NAME: ClassVar[str] = __app_config_name__.lower()

    DEFAULT_SETTINGS_LOCATIONS: ClassVar[list[Path]] = [
        Path("config.toml"),
        Path(platformdirs.user_config_dir(APP_NAME, appauthor=False) / Path(CONF_NAME)),
        Path(platformdirs.site_config_dir(APP_NAME, appauthor=False) / Path(CONF_NAME)),
        str(files(APP_NAME) / CONF_NAME),
    ]

    DEFAULT_CONFIG: ClassVar[dict[str, dict[str, Any]]] = {
        "logger": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_directory": str(platformdirs.user_log_dir(APP_NAME, appauthor=False)),
            "output_format": "console",
        },
        "console_handler": {"enabled": False},
        "file_handler": {
            "enabled": True,
            "file_name": APP_NAME + ".log",
        },
        "limited_file_handler": {
            "enabled": True,
            "file_name": "limited_" + APP_NAME + ".log",
            "max_bytes": 1024,
            "backup_count": 5,
        },
        "gui": {
            "enabled": True,
        },
        "reports": {"directory": str(platformdirs.user_data_dir(APP_NAME, appauthor=False))},
        "data": {"directory": str(platformdirs.user_data_dir(APP_NAME, appauthor=False))},
        "network": {
            "timeout": 5,
            "ntp_servers": ["pool.ntp.org"],
            "urls": ["https://example.com"],
        },
    }

    def __init__(self) -> None:
        """
        Initialize the SettingsManager by loading the configuration.

        Attempts to load configuration from known locations. If no valid
        configuration is found, default values are used and written to the
        first writable path.
        """
        # Ensure that during init, these are only set if it's the *first* instantiation
        # If it's a subsequent call due to singleton, don't reset
        if not hasattr(self, "_settings"):
            self._settings: dict[str, dict[str, Any]] = {}
            self._loaded_config_file: Optional[Path] = None
            self._internal_errors: list[str] = []  # Errors specific to this instance's setup
            # This logger will use the bootstrap configuration initially.
            self.logger = structlog.get_logger(__name__)

    @property
    def loaded_config_file(self) -> Optional[Path]:
        return self._loaded_config_file

    @loaded_config_file.setter
    def loaded_config_file(self, path: Path):
        self._loaded_config_file = path

    def load_settings(self, config_path_from_cli: Optional[Path] = None) -> None:
        """
        Load the application settings.

        Prioritizes:
        1. CLI-provided path (if not None and exists)
        2. Predefined default locations
        3. Falls back to default configuration and saves it if no file is found.

        This method is called by SettingsManagerSingleton.initialize_from_context.
        """
        # Reset current settings and errors before loading
        print("DEBUG SettingsManager] Loading settings")
        self._settings = {}
        self._internal_errors = []  # Clear internal errors before a new load attempt

        loaded_config = self._load_config_from_paths(config_path_from_cli)
        self._settings = loaded_config

    def _load_config_from_paths(self, config_path_from_cli: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
        """Load the configuration, prioritizing CLI path, then predefined locations."""
        self.logger.debug("Attempting to load config from predefined paths")
        # 1. Try CLI-provided path first
        if config_path_from_cli:
            self.logger.info("Attempting to load config from CLI specified path", path=str(config_path_from_cli))
            if config_path_from_cli.exists():
                try:
                    print("\n-----------------")
                    print(f"Loaded configuration from {config_path_from_cli}")
                    print("-----------------\n")
                    loaded = self._load_from_file(config_path_from_cli)
                    self.logger.info("Successfully loaded configuration from CLI path", path=str(config_path_from_cli))
                    return loaded
                except (SettingsConfigurationError, ConfigFileNotFoundError) as e:
                    # Log the specific error, but don't stop here, try other paths
                    self.logger.warning(
                        "Failed to load config from CLI path (malformed or access error), trying default locations.",
                        path=str(config_path_from_cli),
                        error=str(e),
                    )
                    self._internal_errors.append(f"CLI config '{config_path_from_cli}' error: {e}")
                    raise
            else:
                self.logger.warning(
                    "Specified configuration file via CLI does not exist. Searching predefined locations.",
                    path=str(config_path_from_cli),
                )
                self._internal_errors.append(f"CLI config '{config_path_from_cli}' not found.")

        # 2. Search predefined locations
        self.logger.info(
            "Searching for configuration file in predefined locations",
            locations=[str(p) for p in self.DEFAULT_SETTINGS_LOCATIONS],
        )
        for path_candidate in self.DEFAULT_SETTINGS_LOCATIONS:
            path = Path(path_candidate)  # Ensure it's a Path object
            self.logger.debug("Checking predefined config location", path=str(path))
            if path.exists():
                try:
                    loaded = self._load_from_file(path)
                    self.logger.debug("Found and loaded configuration from predefined location", path=str(path))
                    return loaded
                except (SettingsConfigurationError, ConfigFileNotFoundError) as e:
                    self.logger.warning(
                        "Predefined config file malformed or access error, trying next location.",
                        path=str(path),
                        error=str(e),
                    )
                    self._internal_errors.append(f"Predefined config '{str(path)}' error: {e}")
                    raise
            else:
                self.logger.debug("Predefined config location does not exist", path=str(path))

        # 3. No configuration file found after all attempts; use default
        self.logger.warning("No valid configuration file found; using default settings.")
        self._internal_errors.append("No configuration file found; using default settings.")
        # Attempt to save default config, but don't prevent return of defaults if saving fails
        try:
            self._save_default_config()
        except SettingsWriteConfigurationError as e:
            self.logger.exception("Failed to save default configuration after falling back to defaults.", error=str(e))
            self._internal_errors.append(f"Failed to save default config: {e}")
            raise

        return self.DEFAULT_CONFIG.copy()  # Always return a copy to prevent external modification

    def _load_from_file(self, path: Path) -> Dict[str, Dict[str, Any]]:
        """
        Load configuration from a specific file path.

        Raises: SettingsConfigurationError, ConfigFileNotFoundError
        """
        self.logger.info("Loading configuration from file", path=str(path))
        try:
            with path.open("rb") as f:
                config = tomllib.load(f)
            print("\n-----------------")
            print(f"Loaded configuration from {path}")
            print("-----------------\n")
            self.loaded_config_file = path  # Track the loaded config file
            return config
        except tomllib.TOMLDecodeError as e:
            self._internal_errors.append(f"TOML decoding failed for '{str(path)}': {e}")
            self.logger.exception("TOML decoding failed for configuration file", path=str(path))
            raise SettingsConfigurationError(f"Malformed TOML file: {str(path)}") from e
        except (
            OSError
        ) as e:  # Catch file-related OS errors (e.g., permissions, not found if path.exists() failed somehow)
            self._internal_errors.append(f"OS error accessing config file '{str(path)}': {e}")
            self.logger.exception("Operating system error accessing configuration file", path=str(path))
            raise ConfigFileNotFoundError(f"Could not access file: {str(path)}") from e  # Renamed exception for clarity
        except Exception as e:
            self._internal_errors.append(f"Unexpected error loading config '{str(path)}': {e}")
            self.logger.exception("Unexpected error while loading configuration", path=str(path))
            raise SettingsConfigurationError(f"Unexpected error loading config: {str(path)}") from e

    def _save_default_config(self) -> None:
        """
        Write the default configuration to the first writable location.
        Raises: SettingsWriteConfigurationError if no location is writable.
        """
        for path_candidate in self.DEFAULT_SETTINGS_LOCATIONS:  # Use DEFAULT_SETTINGS_LOCATIONS
            path = Path(path_candidate)
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as f:
                    tomli_w.dump(self.DEFAULT_CONFIG, f)
                self.logger.info("Default configuration written successfully.", path=str(path))
                self.loaded_config_file = path
                return  # Successfully saved, so exit
            except (OSError, PermissionError) as e:
                self.logger.exception(
                    "Unable to write default configuration to this location.", path=str(path), error=str(e)
                )
                self._internal_errors.append(f"Failed to save default config to '{str(path)}': {e}")
                raise SettingsWriteConfigurationError("Unable to write default configuration to this location.") from e
            except Exception as e:
                self.logger.warning(
                    self._("Unexpected error while attempting to save default config to this location, trying next."),
                    path=str(path),
                    error=str(e),
                )
                self._internal_errors.append(f"Unexpected error saving default config to '{str(path)}': {e}")
                raise SettingsWriteConfigurationError(
                    "Unexpected error while attempting to save default config to this location, trying next."
                ) from e

        self.logger.error("Failed to write default configuration to any specified location.")
        raise SettingsWriteConfigurationError("Could not save default configuration to any valid location.")

    def _save_config(self) -> None:
        """
        Saves the current configuration to the loaded file path, or the first writable location.
        """
        target_file: Optional[Path] = None

        if self._loaded_config_file:  # Use the private attribute consistent with property
            try:
                self._loaded_config_file.parent.mkdir(parents=True, exist_ok=True)
                # Test writability by attempting to open in write mode
                with self._loaded_config_file.open("wb") as f:
                    pass
                target_file = self._loaded_config_file
                self.logger.info("Attempting to save config to loaded file", path=str(target_file))
            except (OSError, PermissionError) as e:
                self.logger.warning(
                    "Loaded configuration file is not writable, attempting other locations.",
                    path=str(self._loaded_config_file),
                    error=str(e),
                )
                target_file = None
                raise
            except Exception:
                self.logger.exception(
                    "Unexpected error when checking writability of loaded config file for saving",
                    path=str(self._loaded_config_file),
                )
                target_file = None
                raise

        if not target_file:
            self.logger.info("Searching for a writable location to save configuration.")
            for path_candidate in self.DEFAULT_SETTINGS_LOCATIONS:  # Use DEFAULT_SETTINGS_LOCATIONS
                path = Path(path_candidate)
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    # Test writability
                    with path.open("wb") as f:
                        pass
                    target_file = path
                    self.logger.info("Found writable location for saving", path=str(target_file))
                    break
                except (OSError, PermissionError) as e:
                    self.logger.exception(
                        "Location not writable for saving configuration", path=str(path), error=str(e)
                    )
                    raise SettingsWriteConfigurationError("Location not writable for saving configuration")
                except Exception:
                    self.logger.exception("Unexpected error when checking writability for saving", path=str(path))
                    raise SettingsWriteConfigurationError("Unexpected error when checking writability for saving")

        if target_file:
            try:
                with target_file.open("wb") as f:
                    tomli_w.dump(self._settings, f)  # Use self._settings
                self.logger.info("Configuration saved successfully.", path=str(target_file))
                self._loaded_config_file = target_file  # Update the loaded file
            except (OSError, PermissionError) as e:
                self.logger.exception(
                    "Failed to save configuration due to OS/permission error", path=str(target_file), error=str(e)
                )
                raise
            except Exception:
                self.logger.exception("Unexpected error while saving configuration", path=str(target_file))
                raise
        else:
            self.logger.error("No writable location available for saving configuration.")
            # Depending on your design, you might want to raise an exception here too if saving is critical
            raise ValueError("No writable location available for saving configuration.")

    def copy(self) -> dict[str, dict[str, Any]]:
        """
        Return a deep copy of the current configuration.

        Returns
        -------
            dict[str, dict[str, Any]]: Deep copy of the configuration.

        """
        return copy.deepcopy(self._settings)

    def set_setting(self, section: str, key: str, value: Any) -> None:
        if section not in self._settings:
            self._settings[section] = {}
        self._settings[section][key] = value

    def get_all_settings(self) -> dict[str, Any]:
        return copy.deepcopy(self._settings)

    def get(self, section: str, key: str, default: T | None = None) -> T | Any:  # für Any
        """
        Retrieve a value from the configuration with optional default.

        Args:
        ----
            section (str): Section name in the configuration.
            key (str): Key within the section.
            default (Any, optional): Value to return if key is not found.

        Returns:
        -------
            Any: The configuration value, or the provided default.

        """
        value = self._settings.get(section, {}).get(key)
        if value is not None:
            return value
        return default

    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        return self._settings.get(section, {}).get(key, default)

    def get_section(self, section: str) -> dict[str, Any]:
        """
        Retrieve a value from the configuration with optional default.

        Args:
        ----
            section (str): Section name in the configuration.
            key (str): Key within the section.
            default (Any, optional): Value to return if key is not found.

        Returns:
        -------
            Any: The configuration value, or the provided default.

        """
        return self._settings.get(section, {})

    def as_dict(self) -> dict[str, dict[str, Any]]:
        """Return the full config dict."""
        return copy.deepcopy(self._settings)

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Update a configuration value and persist the change to disk.

        Args:
        ----
            section (str): Section name in the configuration.
            key (str): Key to update or create.
            value (Any): New value to set.

        This method modifies the in-memory config and saves it immediately.

        """
        if section not in self._settings:
            self._settings[section] = {}
        self._settings[section][key] = value
        self.logger.debug("Set config value", section=section, key=key, value=value)
        self._save_config()

    def reload(self) -> None:
        """
        Reloads configuration from the disk, prioritizing the previously loaded file.
        If no file was previously loaded, or if it's no longer valid,
        it attempts to re-search predefined locations.
        """
        self.logger.debug("Reloading configuration from disk")

        # Key change: Use the *stored* _loaded_config_file for reload if available
        if self._loaded_config_file and self._loaded_config_file.exists() and self._loaded_config_file.is_file():
            self.logger.info(f"Reloading from previously loaded path: {self._loaded_config_file}")
            try:
                reloaded_config = self._load_from_file(self._loaded_config_file)
                self._settings = reloaded_config
                self.logger.info("Successfully reloaded configuration from previous path.")
            except (SettingsConfigurationError, ConfigFileNotFoundError, OSError) as e:
                self.logger.warning(
                    f"Failed to reload from previous path ({self._loaded_config_file}), attempting re-search.",
                    error=str(e),
                )
                self._loaded_config_file = None  # Invalidate the path if it failed
                self.load_settings(config_path_from_cli=None)  # Fallback to a fresh search
            except Exception as e:
                self.logger.exception(
                    f"Unexpected error during reload from previous path: {self._loaded_config_file}", error=str(e)
                )
                self._loaded_config_file = None
                self.load_settings(config_path_from_cli=None)  # Fallback
        else:
            self.logger.warning(
                "No valid previously loaded config path or path is no longer valid for reload. Attempting to re-search."
            )
            # If no previous path, or it's invalid, trigger a full search
            self.load_settings(config_path_from_cli=None)

    def save(self) -> None:
        """Persist current configuration to disk."""
        self._save_config()

    def get_instance_errors(self) -> list[str]:
        """Exposes internal errors encountered during configuration."""
        return list(self._internal_errors)


class SettingsManagerSingleton:
    """
    Singleton class for SettingsManager.

    That ensure a single instance
    manages application settings.
    """

    _instance: SettingsManager | None = None
    _initialization_errors: ClassVar[list[str]] = []
    _is_configured: ClassVar[bool] = False  # Track if the instance has been configured

    @classmethod
    def get_instance(cls) -> SettingsManager:
        """
        Return the single instance of SettingsManager.

        Raises RuntimeError if not yet initialized.
        """
        if cls._instance is None:
            try:
                cls._instance = SettingsManager()  # Default creation
            except Exception as e:
                cls._initialization_errors.append(f"Error creating SettingsManager instance: {e}")
                cls._instance = None
                raise  # Re-raise
        return cls._instance

    @classmethod
    def initialize_from_context(cls, config_path: Path | None = None) -> None:
        """
        Initialize the SettingsManager instance with a specific config path.

        This should be called *after* getting the instance and
        before using it.
        """
        print("[DEBUG] initialize_from_context was called")
        print("[DEBUG] initialize_from_context was called. cls._is_configured: ", cls._is_configured)

        if cls._is_configured:
            print("SettingsManagerSingleton already configured. Cannot re-configure.")
            cls._initialization_errors.append("SettingsManagerSingleton already configured. Cannot re-configure.")
            return  # Prevent re-initialization

        print("[DEBUG] initialize_from_context was called. cls._instance: ", cls._instance)

        if cls._instance is None:
            try:
                cls._instance = cls.get_instance()
            except Exception as e:
                cls._initialization_errors.append(f"Error initializing SettingsManagerSingleton: {e}")
                cls._instance = None
                raise  # Re-raise critical creation error

            cls._initialization_errors.append("SettingsManagerSingleton already initialized. Cannot re-initialize.")
            return  # Prevent re-initialization

        cls._initialization_errors.clear()  # Clear errors for a fresh initialization attempt

        try:
            print("[DEBUG by INIT] configure_settings: ", config_path)

            cls._instance.load_settings(config_path)  # Call the instance's load_settings
            # Add any errors reported by the instance itself
            cls._initialization_errors.extend(cls._instance.get_instance_errors())
        except Exception as e:
            # Critical error during settings initialization
            cls._initialization_errors.append(f"Unexpected error during SettingsManager initialization: {e}")
            raise  # Re-raise if initialization failed critically

    @classmethod
    def get_initialization_errors(cls) -> list[str]:
        """Exposes initialization errors for testing/debugging."""
        errors = list(cls._initialization_errors)
        if cls._instance:
            errors.extend(cls._instance.get_instance_errors())  # Now calling public method
        return list(set(errors))  # Return unique errors

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance and its configuration state.

        Primarily for testing.
        """
        cls._instance = None
        cls._initialization_errors.clear()
        cls._is_configured = False
