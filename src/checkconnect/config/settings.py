# SPDX-FileCopyrightText: © 2023-2024 Jürgen Mülbert
#
# SPDX-License-Identifier: EUPL-1.2


"""
Store and retrieve configuration settings.

This class provides methods to read configuration settings from a config
file and environment variables. It checks the config for the current
environment first, then falls back to the 'default' config section if not
found.
"""

from __future__ import annotations

from configparser import ConfigParser
from os import getenv
from typing import Any


class Settings:
    """
    Provides a Settings class to manage configuration settings for the application.

    The Settings class reads in configuration settings from a file and provides
    methods to retrieve those settings. It supports reading settings from
    different environments (e.g. 'dev', 'prod') and falling back to default
    values if a setting is not found.

    The Settings class is responsible for initializing the configuration
    parser, reading the configuration file, and providing a consistent interface
    for retrieving settings.
    """

    __slots__ = ["config_parser", "env"]
    config_parser: ConfigParser
    env: str

    def __init__(self, file: str = "settings.conf") -> None:
        """Initializes the Settings class.

        Reads in the configuration from the provided file path.
        Sets the ENV environment variable to 'dev' if not already set.
        """
        self.config_parser = ConfigParser()
        self.config_parser.read(file)
        self.env = getenv("ENV", "dev")

    def get(self, name: str, default_value: Any = None) -> Any:
        """Gets the value for the given setting name from the environment
        configuration.

        First checks the configuration for the current ENV environment.
        If not found, checks the 'default' environment configuration.
        If still not found, returns the provided default value.

        Args:
        ----
            name: The name of the setting to get.
            default_value: The value to return if no value found for the setting.

        Returns:
        -------
            The value for the setting, or the default value if not found.

        """
        return self._get_from_section(self.env, name) or self._get_from_section("default", name) or default_value

    def _get_from_section(self, section: str, var: str) -> Any:
        """Gets the value for the given setting name from the given config
        section.

        Checks if the given section exists in the config parser and if the
        given setting name exists in that section. If found, returns the
        setting value. Otherwise returns None.

        Args:
        ----
            section: The section in the config to check.
            var: The name of the setting to get.

        Returns:
        -------
            The setting value if found, else None.

        """
        if section in self.config_parser and var in self.config_parser[section]:
            return self.config_parser[section][var]
        return None


settings = Settings()
