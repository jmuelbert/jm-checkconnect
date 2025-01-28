# SPDX-FileCopyrightText: © 2023-2024 Jürgen Mülbert
#
# SPDX-License-Identifier: EUPL-1.2

from __future__ import annotations

import os
from unittest import TestCase, mock

from checkconnect.config.settings import Settings


class SettingsTest(TestCase):
    """Tests for reading configuration settings from a file.

    This test suite verifies that Settings class can:

    - Read values from a settings file and make them available
    - Return a default when a setting is not found
    - Parse settings as int, float, etc. based on type
    - Read environment-specific overrides

    tests are organized into unit tests for each of these behaviors.
    """

    def setUp(self) -> None:
        """Sets up the Settings instance to test.

        Creates a Settings instance initialized with
        settings_to_test.conf file for testing purposes.
        """

        self.settings = Settings(file="./tests/config/settings_to_test.conf")

    def test_get_setting_value_with_success(self) -> None:
        """Tests that get() method returns correct
        setting value for a given setting key. Verifies
        get() method returns expected value for
        a valid setting key.
        """
        assert self.settings.get("app_name") == "app-name"

    def test_get_default_value_when_setting_not_found_with_success(
        self,
    ) -> None:
        """Tests that get() method returns default value
        when setting key is not found in settings file.
        Verifies get() returns expected default value when
        given an invalid setting name.
        """
        assert self.settings.get("not_found_var", "default_value") == "default_value"

    def test_get_setting_int_value_with_success(self) -> None:
        """Tests that get() method parses and returns
        integer values correctly. Verifies that get() will
        cast setting value to an integer if setting
        type is int.
        """
        assert int(self.settings.get("sample_of_int_var")) == 10

    def test_get_setting_float_value_with_success(self) -> None:
        """Tests that get() method parses and returns
        float values correctly. Verifies that get() will
        cast setting value to a float if setting
        type is float.
        """
        assert float(self.settings.get("sample_of_float_var")) == 10.1

    @mock.patch.dict(os.environ, {"ENV": "prod"}, clear=True)
    def test_get_setting_value_from_production_env_with_success(self) -> None:
        """Creates a Settings instance initialized for production
        environment, loading config from given file path.
        """
        prod_settings = Settings(file="./tests/config/settings_to_test.conf")
        assert prod_settings.get("app_var") == "prod-app-var"

    @mock.patch.dict(os.environ, {"ENV": "qa"}, clear=True)
    def test_get_setting_value_from_qa_env_with_success(self) -> None:
        """Creates a Settings instance initialized for QA
        environment, loading config from given file path."""
        qa_settings = Settings(file="./tests/config/settings_to_test.conf")
        assert qa_settings.get("app_var") == "qa-app-var"

    @mock.patch.dict(os.environ, {"ENV": "test"}, clear=True)
    def test_get_setting_value_from_test_env_with_success(self) -> None:
        """Creates a Settings instance initialized for test
        environment, loading config from given file path."""
        test_settings = Settings(file="./tests/config/settings_to_test.conf")
        assert test_settings.get("app_var") == "test-app-var"

    @mock.patch.dict(os.environ, {"ENV": "dev"}, clear=True)
    def test_get_setting_value_from_dev_env_with_success(self) -> None:
        """Creates a Settings instance initialized for dev
        environment, loading config from given file path."""
        dev_settings = Settings(file="./tests/config/settings_to_test.conf")
        assert dev_settings.get("app_var") == "dev-app-var"
