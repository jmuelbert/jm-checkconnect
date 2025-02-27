# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2023-present Jürgen Mülbert

"""
Store and retrieve configuration settings.

This module provides a `Settings` class that reads configuration values from a
configuration file and environment variables. It prioritizes values from the
specified environment section and falls back to the 'default' section if
the key is not found.
"""

import logging
import sys
from configparser import ConfigParser
from os import getenv
from typing import Any

# Configure logging for the application
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # Log to stdout
)
logger = logging.getLogger("checkconnect")


class Settings:
    """
    Manage configuration settings for the application.

    This class reads configurations from a file and provides a method to retrieve
    values based on the current environment (e.g., 'dev', 'prod'). If a setting is
    not found in the active environment, the default section is used as a fallback.

    Attributes
    ----------
        config_parser (ConfigParser): Parses the configuration file.
        env (str): The active environment (default: 'dev').

    """

    __slots__ = ["config_parser", "env"]  # Optimize memory usage
    config_parser: ConfigParser
    env: str

    def __init__(self, file: str = "settings.conf") -> None:
        """
        Initialize the settings manager.

        Args:
        ----
            file (str): Path to the configuration file. Defaults to 'settings.conf'.

        """
        self.config_parser = ConfigParser()
        self.config_parser.read(file)  # Load configuration from file
        self.env = getenv("ENV", "dev")  # Get the active environment from system variables

    def get(self, name: str, default_value: Any = None) -> Any:
        """
        Retrieve a configuration value.

        Tries to get the setting from the active environment first. If not found,
        it falls back to the 'default' section. If still not found, returns the
        provided default value.

        Args:
        ----
            name (str): The name of the configuration variable.
            default_value (Any): The default value to return if the key is not found.

        Returns:
        -------
            Any: The configuration value or the default value if not found.

        """
        return (
            self._get_from_section(self.env, name)  # Try current environment
            or self._get_from_section("default", name)  # Fallback to default section
            or default_value  # Use provided default value
        )

    def _get_from_section(self, section: str, var: str) -> Any:
        """
        Helper function to retrieve a value from a specific section.

        Args:
        ----
            section (str): The section in the config file.
            var (str): The variable name to retrieve.

        Returns:
        -------
            Any: The retrieved value or None if not found.

        """
        if section in self.config_parser and var in self.config_parser[section]:
            return self.config_parser[section][var]
        return None


# Global settings instance to be used throughout the application
settings = Settings()
