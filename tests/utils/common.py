import pytest
from unittest.mock import MagicMock
import logging
from checkconnect.config.appcontext import AppContext


def assert_common_initialization(
    settings_manager_instance: MagicMock,
    logging_manager_instance: MagicMock,
    translation_manager_instance: MagicMock,
    expected_cli_log_level: int,
    expected_language: str,
) -> None:
    """Helper function to assert common application initialization steps."""
    # SettingsManager
    settings_manager_instance.get_all_settings.assert_called_once()
    settings_manager_instance.get_section.assert_called_once_with("logger")

    # TranslationManager: Ensure configure was called
    translation_manager_instance.configure.assert_called_once_with(
        language=expected_language, translation_domain=None, locale_dir=None
    )

    # AppContext: Ensure AppContext.create was called with the correct manager instances
    # Note: AppContext.create should be mocked in your conftest or setup
    AppContext.create.assert_called_once_with(
        settings_instance=settings_manager_instance,
        translator_instance=translation_manager_instance,
    )

    # Logging Manager: Ensure apply_configuration was called
    logging_manager_instance.apply_configuration.assert_called_once_with(
        cli_log_level=expected_cli_log_level,
        enable_console_logging=False,  # Based on your tests, always False
        log_config=settings_manager_instance.get_section("logger"),
        translator=translation_manager_instance,
    )
