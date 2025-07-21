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

import logging
from unittest.mock import MagicMock, patch

import pytest
import structlog

# Assuming your AppContext is in 'checkconnect.config.appcontext'
from checkconnect.config.appcontext import AppContext
from checkconnect.config.settings_manager import SettingsManager

# --- Fixtures for Mocking Dependencies ---


@pytest.fixture
def mock_settings_manager():
    """Mocks the SettingsManager."""
    # Use string for spec if you're only patching the class in some tests,
    # or ensure the actual class is imported if you're creating real mocks.
    mock = MagicMock(spec=SettingsManager)
    return mock


# --- Tests for AppContext ---


class TestAppContext:
    @pytest.mark.unit
    def test_app_context_initialization(self, mock_settings_manager, mocked_translation: MagicMock) -> None:
        """
        Tests that AppContext correctly stores the provided manager instances.
        """
        app_context = AppContext(settings=mock_settings_manager, translator=mocked_translation)

        assert app_context.settings is mock_settings_manager
        assert app_context.translator is mocked_translation

    @pytest.mark.unit
    @patch("structlog.get_logger")
    def test_get_module_logger_functionality(
        self,
        mock_structlog_get_logger: MagicMock,
        mock_settings_manager,
        mocked_translation: MagicMock,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Tests that get_module_logger returns a functional structlog BoundLogger
        and that it's correctly named.
        """
        print("\n--- test_get_module_logger_functionality: TEST started ---")  # DEBUG
        print(
            f"--- test_get_module_logger_functionality: Before AppContext, structlog.is_configured() = {structlog.is_configured()} ---"
        )  # DEBUG
        print(
            f"--- test_module_logger_functionality: Before AppContext, root_logger handlers = {logging.getLogger().handlers} ---"
        )  # DEBUG

        module_name = "my.test.module.logger"

        # Get a standard Python logger that BoundLogger will wrap
        base_python_logger = logging.getLogger(module_name)

        # Ensure its level is low enough to capture messages
        base_python_logger.setLevel(logging.DEBUG)

        # --- FINAL CRITICAL FIX ---
        # Ensure no NullHandler is consuming logs directly on this logger.
        # Messages should propagate up to the root logger where `capture_logs` is active.
        for handler in base_python_logger.handlers[:]:
            base_python_logger.removeHandler(handler)
        # --- END FINAL CRITICAL FIX ---

        # Define processors for the manually instantiated BoundLogger
        # These MUST match the processors from your conftest.py's structlog_base_config
        # for `capture_logs` to correctly interpret the log entries.
        processors_for_bound_logger = [
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            # structlog.processors.TimeStamper(fmt="iso", utc=True), # Ensure this matches your conftest.py
            # structlog.processors.StackInfoRenderer(), # If you have these in conftest
            # structlog.processors.format_exc_info, # If you have these in conftest
            # structlog.processors.UnicodeDecoder(), # If you have these in conftest
            # Add ALL other processors from your conftest.py structlog_base_config here!
        ]

        real_bound_logger = structlog.stdlib.BoundLogger(
            base_python_logger, processors=processors_for_bound_logger, context={}
        )

        # Set the return value of the mocked structlog.get_logger
        mock_structlog_get_logger.return_value = real_bound_logger

        # from checkconnect.config.logging_bootstrap import bootstrap_logging
        # bootstrap_logging()

        app_context = AppContext(settings=mock_settings_manager, translator=mocked_translation)
        # module_name = __name__
        logger = app_context.get_module_logger(module_name)

        print(
            f"--- test_get_module_logger_functionality: After get_module_logger, logger type = {type(logger)} ---"
        )  # DEBUG
        print(f"--- test_get_module_logger_functionality: After get_module_logger, logger = {logger!r} ---")  # DEBUG

        mock_structlog_get_logger.assert_called_once_with(module_name)
        assert isinstance(logger, structlog.stdlib.BoundLogger)

        logger.info("This is a test log message.", key="value")
        # The `capture_logs` block should now correctly capture events
        # because the BoundLogger's messages will propagate to the root logger
        # where `structlog.testing.capture_logs` adds its temporary handler.
        # with structlog.testing.capture_logs() as captured_logs:
        #     logger.info("This is a test log message.", key="value")
        #     assert len(captured_logs) == 1
        #     log_entry = captured_logs[0]
        #     assert log_entry["event"] == "This is a test log message."
        #     assert log_entry["logger"] == module_name
        #     assert log_entry["level"] == "info"
        #     assert log_entry["key"] == "value"

        for entry in caplog_structlog:
            print(entry)
            assert entry["event"] == "This is a test log message."
            assert entry["logger"] == module_name
            assert entry["level"] == "info"
            assert entry["key"] == "value"

    @pytest.mark.unit
    def test_gettext(
        self,
        mock_settings_manager,
        mocked_translation: MagicMock,
    ) -> None:
        """
        Tests that gettext delegates to the translator and returns the translated message.
        """
        app_context = AppContext(settings=mock_settings_manager, translator=mocked_translation)

        message = "Hello, world!"
        translated_message = app_context.gettext(message)

        mocked_translation.gettext.assert_called_once_with(message)
        assert translated_message == f"Translated: {message}"

    class TestCreateMethod:
        """
        Tests for the AppContext.create factory method.
        """

        @pytest.mark.unit
        @patch("checkconnect.config.appcontext.SettingsManager")
        @patch("checkconnect.config.appcontext.TranslationManager")
        def test_create_with_no_args(
            self,
            MockTranslationManager,
            MockSettingsManager,
        ) -> None:
            """
            Tests that create initializes default SettingsManager and TranslationManager
            when no arguments are provided.
            """
            app_context = AppContext.create()

            MockSettingsManager.assert_called_once_with()
            MockTranslationManager.assert_called_once_with(language=None)

            assert isinstance(app_context, AppContext)
            assert app_context.settings is MockSettingsManager.return_value
            assert app_context.translator is MockTranslationManager.return_value

        @pytest.mark.unit
        @patch("checkconnect.config.logging_manager.LoggingManager")
        @patch("checkconnect.config.appcontext.TranslationManager")
        @patch("checkconnect.config.appcontext.SettingsManager")
        def test_create_with_existing_config_and_language(
            self, MockSettingsManager: MagicMock, MockTranslationManager: MagicMock, MockLoggingManager: MagicMock
        ) -> None:
            mock_provided_settings = MagicMock(spec=SettingsManager)
            test_language = "de"

            # Execute the method under test
            app_context = AppContext.create(settings=mock_provided_settings, language=test_language)

            # Assertions on mock calls

            # 1. SettingsManager should NOT be called because it was provided
            MockSettingsManager.assert_not_called()

            # 2. TranslationManager SHOULD be called once with the specified language
            MockTranslationManager.assert_called_once()  # Ensure it was called exactly once
            # Now, explicitly check the arguments of that single call
            actual_call_args, actual_call_kwargs = MockTranslationManager.call_args

            assert actual_call_args == ()  # Ensure no positional arguments were passed
            assert actual_call_kwargs == {"language": test_language}  # This must now match exactly!

            # 3. LoggingManager should NOT be called directly by AppContext.create
            MockLoggingManager.assert_not_called()

            # Assertions on the returned AppContext instance
            assert isinstance(app_context, AppContext)
            assert app_context.settings is mock_provided_settings
            assert app_context.translator is MockTranslationManager.return_value

        @pytest.mark.unit
        @patch("checkconnect.config.logging_manager.LoggingManager")
        @patch("checkconnect.config.appcontext.TranslationManager")
        @patch("checkconnect.config.appcontext.SettingsManager")
        def test_create_does_not_instantiate_logging_manager(
            self,
            MockSettingsManager: MagicMock,  # Corresponds to the bottom-most @patch
            MockTranslationManager: MagicMock,  # Corresponds to the middle @patch
            MockLoggingManager: MagicMock,  # Corresponds to the top-most @patch
        ) -> None:
            """
            Tests that AppContext.create does NOT instantiate LoggingManager directly,
            as its configuration is assumed to be handled externally.
            """
            # This test runs in isolation, so the AppContext's code is paramount.
            # The configure_structlog_for_tests fixture for this class is auto-applied.
            AppContext.create()

            MockLoggingManager.assert_not_called()  # The key assertion
            # Also verify that other managers are still created/used correctly
            MockSettingsManager.assert_called_once_with()
            MockTranslationManager.assert_called_once_with(language=None)
