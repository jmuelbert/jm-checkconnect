# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Pytest suite for the AppContext class and its initialization.

This module contains unit tests for the `AppContext` class and the
`initialize_app_context` function. It ensures their correct functionality,
initialization of dependencies, resource access, and proper handling of
various input scenarios, including default values and exception propagation.
Pytest-mock is used to isolate units under test by mocking external
dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

# Assuming AppContext is located at checkconnect/app_context.py
# Adjust the import path if your file structure is different.
from checkconnect.config.appcontext import initialize_app_context

if TYPE_CHECKING:
    from pathlib import Path


# --- Tests for AppContext and initialize_app_context ---


# These patches target where the objects are used within the appcontext.py file itself.
@patch("checkconnect.config.appcontext.SettingsManager")
@patch("checkconnect.config.appcontext.AppContext.create")  # Patch AppContext.create directly
class TestAppContextInitialization:
    """
    Test suite for the `initialize_app_context` function, focusing on its
    orchestration of `SettingsManager` and `AppContext.create`.

    Note: This suite mocks `SettingsManager` and `AppContext.create`.
    Detailed testing of `AppContext`'s internal dependency management (e.g.,
    `LoggingManager`, `TranslationManager`) should be handled in separate
    unit tests specifically for `AppContext.create` itself.
    """

    @pytest.mark.unit
    def test_initialize_app_context_success(
        self,
        mock_app_context_create: MagicMock,  # This is the mock for AppContext.create
        mock_settings_manager: MagicMock,
        config_file: Path,
    ) -> None:
        """
        Tests the successful initialization of AppContext via `initialize_app_context`
        with explicit config_file and language.

        Verifies that:
        - `SettingsManager` is instantiated with the provided `config_file`.
        - `AppContext.create` is called with the instantiated `SettingsManager` mock
          and the specified language.
        - The function returns the mock `AppContext` instance.
        """
        # Arrange
        test_language = "en"
        # mock_settings_instance will be the mock object that `SettingsManager()` returns
        mock_settings_instance = mock_settings_manager.return_value
        # mock_app_context_instance will be the mock object that `AppContext.create()` returns
        mock_app_context_instance = mock_app_context_create.return_value

        # Act
        # Call the actual function under test: initialize_app_context
        returned_app_context = initialize_app_context(config_file=config_file, language=test_language)

        # Assert

        # 1. Verify that SettingsManager was instantiated with the correct config_file
        mock_settings_manager.assert_called_once_with(config_file=config_file)

        # 2. Verify that AppContext.create was called with the *mock instance* of SettingsManager
        #    and the correct language.
        mock_app_context_create.assert_called_once_with(config=mock_settings_instance, language=test_language)

        # 3. Verify that `initialize_app_context` returned what `AppContext.create` returned.
        assert returned_app_context == mock_app_context_instance

    @pytest.mark.unit
    def test_initialize_app_context_no_config_file_no_language(
        self,
        mock_app_context_create: MagicMock,
        mock_settings_manager: MagicMock,
    ) -> None:
        """
        Tests `initialize_app_context` when no `config_file` or `language` is provided.

        Verifies that:
        - `SettingsManager` is instantiated with `config_file=None`.
        - `AppContext.create` is called with the instantiated `SettingsManager` mock
          and `language=None`.
        - The function returns the mock `AppContext` instance.
        """
        # Arrange
        # mock_settings_instance will be the mock object that `SettingsManager()` returns
        mock_settings_instance = mock_settings_manager.return_value
        # mock_app_context_instance will be the mock object that `AppContext.create()` returns
        mock_app_context_instance = mock_app_context_create.return_value

        # Act
        # Call the function without arguments
        returned_app_context = initialize_app_context()

        # Assert

        # 1. Verify that SettingsManager was instantiated WITHOUT a config_file argument
        #    This means it was called like SettingsManager(), not SettingsManager(config_file=...)
        mock_settings_manager.assert_called_once_with(
            config_file=None
        )  # Or just assert_called_once_with() if config_file is the only optional param

        # 2. Verify that AppContext.create was called with the mock SettingsManager instance
        #    and with language=None (the default).
        mock_app_context_create.assert_called_once_with(config=mock_settings_instance, language=None)

        # 3. Verify that `initialize_app_context` returned what `AppContext.create` returned.
        assert returned_app_context == mock_app_context_instance

    @pytest.mark.unit
    def test_initialize_app_context_settings_manager_raises_exception(
        self, mock_app_context_create: MagicMock, mock_settings_manager: MagicMock, config_file: Path
    ) -> None:
        """
        Tests that `initialize_app_context` correctly propagates exceptions
        raised during the `AppContext.create` call.

        Verifies that:
        - `SettingsManager` is instantiated correctly before the exception occurs.
        - `AppContext.create` is called with the expected arguments before
          raising its side effect.
        - The `RuntimeError` is raised by `initialize_app_context`.
        """
        # Arrange
        mock_app_context_create.side_effect = RuntimeError("AppContext creation failed")
        test_language = "fr"

        # Act & Assert
        with pytest.raises(RuntimeError, match="AppContext creation failed"):
            initialize_app_context(config_file=config_file, language=test_language)

        # Assertions to ensure calls happened before exception
        mock_settings_manager.assert_called_once_with(config_file=config_file)
        mock_app_context_create.assert_called_once_with(
            config=mock_settings_manager.return_value, language=test_language
        )
