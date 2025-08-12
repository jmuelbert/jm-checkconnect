# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

from typing import TYPE_CHECKING

from checkconnect.config.appcontext import AppContext

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from structlog.typing import EventDict

def assert_common_initialization(
    *,
    settings_manager_instance: MagicMock,
    logging_manager_instance: MagicMock,
    translation_manager_instance: MagicMock,
    expected_cli_log_level: int,
    expected_language: str = "en",
    expected_console_logging: bool = True,
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
        enable_console_logging=expected_console_logging,  # Based on your tests, always False
        log_config=settings_manager_instance.get_section("logger"),
        translator=translation_manager_instance,
    )


def assert_common_cli_logs(log_entries: list[EventDict]) -> None:
    # 1. Assert initial CLI startup (DEBUG)
    assert any(e.get("event") == "Main callback: is starting!" and e.get("log_level") == "debug" for e in log_entries)

    # 2. Assert key INFO level success messages
    assert any(
        e.get("event") == "Main callback: SettingsManager initialized and configuration loaded."
        and e.get("log_level") == "info"
        for e in log_entries
    )
    assert any(
        e.get("event") == "Main callback: TranslationManager initialized." and e.get("log_level") == "info"
        for e in log_entries
    )
    assert any(
        e.get("event") == "Main callback: Full logging configured based on application settings and CLI options."
        and e.get("log_level") == "info"
        for e in log_entries
    )

    # 4. Assert CLI-Verbose and Logging Level determination (DEBUG)
    assert any(
        e.get("event") == "Main callback: Determined CLI-Verbose and Logging Level to pass to LoggingManager."
        and e.get("log_level") == "debug"
        and e.get("verbose_input") == 0
        and e.get("derived_cli_log_level") == "WARNING"
        for e in log_entries
    )

    # 5. Assert "Debug logging is active" (DEBUG)
    # This one is tricky if it *always* appears when `log_entries` captures at DEBUG.
    # If it specifically means the *application* is running in debug, then assert.
    # If it's just reflecting your test setup's debug level, it's less of a functional assertion.
    assert any(
        e.get("event") == "Debug logging is active based on verbosity setting." and e.get("log_level") == "debug"
        for e in log_entries
    )

def clean_cli_output(output: str) -> str:
    """
    Normalize CLI output for consistent testing.

    - Collapses all whitespace (including newlines) to single spaces.
    - Strips leading/trailing whitespace.
    - Removes Rich frames or box-drawing characters.

    Args:
        output: The raw CLI output string.

    Returns:
        Cleaned and normalized string for assertions.
    """
    # Optional: remove common Rich box-drawing characters
    box_chars = "".join(chr(c) for c in range(0x2500, 0x257F))
    translation_table = str.maketrans("", "", box_chars)

    # Remove box characters and normalize whitespace
    return " ".join(output.translate(translation_table).split()).strip()
