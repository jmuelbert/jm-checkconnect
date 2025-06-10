# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""Tests for the GUI entry point and startup logic."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from checkconnect.gui.gui_main import CheckConnectGUIRunner
from checkconnect.gui.startup import run, setup_translations

if TYPE_CHECKING:
    from pytest.logging import LogCaptureFixture  # noqa: PT013 from RUFF for this line
    from pytest_mock import MockerFixture

    from checkconnect.config.appcontext import AppContext


class TestSetupTranslations:
    """Unit tests for the setup_translations function."""

    @pytest.mark.parametrize("language", ["en", "es", "de", "ko", "jp", "zh_CN"])
    def test_several_languages(
        self,
        app_context_fixture: AppContext,
        mock_qapplication_class: MagicMock,
        mocker: MockerFixture,
        language: str,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that setup_translations attempts to load the correct .qm file for various languages.

        This test verifies that the `QTranslator.load` method is called with the
        expected resource path for different language codes.

        Args:
            app_context_fixture (AppContext): The mocked application context.
            mocker (MockerFixture): The pytest-mock fixture.
            mock_qapplication_class (MagicMock): The mocked QApplication instance.
            language (str): The language code to test.
            caplog (LogCaptureFixture): The pytest fixture to capture log messages.
        """
        caplog.set_level(10)  # Set logging level to DEBUG to capture all messages

        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        translator.load.return_value = True  # Simulate successful load from resource

        setup_translations(app=mock_qapplication_class, context=app_context_fixture, language=language)

        translation_file = f":/translations/{language}.qm"
        translator.load.assert_called_once_with(translation_file)
        assert any(
            f"[mocked] Loaded Qt translations from Qt resource: {translation_file}" in record.message
            for record in caplog.records
        )

    def test_without_language(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that setup_translations defaults to system locale (en) when no language is specified.

        This test ensures that if no explicit language is provided, the function
        attempts to load the "en.qm" translation file by default, simulating
        the system's UI language.

        Args:
            app_context_fixture (AppContext): The mocked application context.
            mocker (MockerFixture): The pytest-mock fixture.
            mock_qapplication_class (MagicMock): The mocked QApplication instance.
            caplog (LogCaptureFixture): The pytest fixture to capture log messages.
        """
        caplog.set_level(10)

        # Correct way to mock QLocale.system() and its return value's methods
        mock_qlocale_instance = mocker.MagicMock()
        mock_qlocale_instance.uiLanguages.return_value = []  # Simulate no preferred UI languages
        mock_qlocale_instance.name.return_value = "en_US"  # Simulate system locale name
        mocker.patch("PySide6.QtCore.QLocale.system", return_value=mock_qlocale_instance)

        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        translator.load.return_value = True
        setup_translations(app=mock_qapplication_class, context=app_context_fixture)
        translator.load.assert_called_once_with(":/translations/en.qm")
        assert any(
            "Qt preferred UI languages not found, falling back to system locale: en" in record.message
            for record in caplog.records
        )

    def test_loads_from_resource(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that translations are successfully loaded from Qt resources.

        Verifies that when `QTranslator.load` is mocked to return `True` for
        the resource path, the `QApplication.installTranslator` is called
        and an info message is logged.

        Args:
            app_context_fixture (AppContext): The mocked application context.
            mocker (MockerFixture): The pytest-mock fixture.
            mock_qapplication_class (MagicMock): The mocked QApplication instance.
            caplog (LogCaptureFixture): The pytest fixture to capture log messages.
        """
        caplog.set_level(10)

        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        translator.load.return_value = True
        setup_translations(mock_qapplication_class, app_context_fixture, "en")
        translator.load.assert_called_once_with(":/translations/en.qm")
        mock_qapplication_class.installTranslator.assert_called_once_with(translator)
        assert any(
            "[mocked] Loaded Qt translations from Qt resource: :/translations/en.qm" in record.message
            for record in caplog.records
        )

    def test_fallback_to_filesystem(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        tmp_path: Path,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that translations fallback to the filesystem if resource loading fails.

        Simulates a failed resource load and a successful filesystem load,
        verifying that both `QTranslator.load` calls occur in sequence and
        the correct success message is logged for the filesystem path.

        Args:
            app_context_fixture (AppContext): The mocked application context.
            mocker (MockerFixture): The pytest-mock fixture.
            mock_qapplication (MagicMock): The mocked QApplication instance.
            tmp_path (Path): A temporary directory fixture provided by pytest.
            caplog (LogCaptureFixture): The pytest fixture to capture log messages.
        """
        caplog.set_level(10)

        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        # First load (resource) fails, second load (filesystem) succeeds
        translator.load.side_effect = [False, True]

        # Create a dummy .qm file in the temporary directory
        file_path = tmp_path / "en.qm"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        setup_translations(mock_qapplication_class, app_context_fixture, "en", translations_dir=tmp_path)

        translator.load.assert_any_call(":/translations/en.qm")
        translator.load.assert_any_call(str(file_path))
        mock_qapplication_class.installTranslator.assert_called_once_with(translator)

        assert any(
            f"[mocked] Loaded Qt translations from file: {file_path}" in record.message for record in caplog.records
        )

    def test_load_fails_completely(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        tmp_path: Path,
        caplog: LogCaptureFixture,
    ) -> None:
        """
        Test that translation loading fails completely if all attempts are unsuccessful.

        Simulates failures for resource, filesystem, and fallback attempts,
        ensuring that appropriate warning messages are logged and no translator
        is installed.

        Args:
            app_context_fixture (AppContext): The mocked application context.
            mocker (MockerFixture): The pytest-mock fixture.
            mock_qapplication_class (MagicMock): The mocked QApplication instance.
            tmp_path (Path): A temporary directory fixture provided by pytest.
            caplog (LogCaptureFixture): The pytest fixture to capture log messages.
        """
        caplog.set_level(10)

        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        # All load attempts fail
        translator.load.side_effect = [False, False, False]

        # Create a dummy en.qm for the final fallback to be attempted (but will fail to load)
        fallback_file = tmp_path / "en.qm"
        fallback_file.touch()

        setup_translations(mock_qapplication_class, app_context_fixture, "en", translations_dir=tmp_path)

        # Assert all load attempts were made
        translator.load.assert_any_call(":/translations/en.qm")
        # Ensure the first filesystem attempt uses the constructed Path
        translator.load.assert_any_call(str(Path(tmp_path) / "en.qm"))
        # Ensure the final fallback attempt uses the same Path object
        translator.load.assert_any_call(str(fallback_file))

        mock_qapplication_class.installTranslator.assert_not_called()

        # Assert the warning messages for each failed attempt
        assert any("[mocked] No Qt translation found for language 'en'" in record.message for record in caplog.records)


class TestRunFunction:
    """Unit tests for the `run` function, the main GUI entry point."""

    @pytest.fixture
    def setup_run_mocks(self, mocker: MockerFixture) -> CheckConnectGUIRunner:
        """
        Set up common mocks for `run` function tests.

        This fixture ensures that `sys.exit` is mocked to prevent actual process
        exits during tests and that `CheckConnectGUIRunner` is mocked to control
        the behavior of the main GUI window.
        It also resets the mocks for QApplication and QApplication.instance()
        to ensure a clean state for each test.

        Args:
            mocker (MockerFixture): The pytest-mock fixture.
            mock_qapplication_class (MagicMock): The mocked QApplication class (constructor).
        """
        # mocker.patch("sys.exit")  # Prevent sys.exit from terminating the test run
        self.mock_window = MagicMock(spec=CheckConnectGUIRunner)
        mocker.patch("checkconnect.gui.gui_main.CheckConnectGUIRunner", return_value=self.mock_window)
        mocker.patch("checkconnect.gui.startup.setup_translations")  # Avoid side effects in test
        return self.mock_window

    def test_run_new_qapplication_instance(
        self,
        app_context_fixture: AppContext,
        mock_qapplication_class: MagicMock,
    ) -> None:
        """
        Test `run` function when a new QApplication instance is created.

        Verifies that `QApplication` is initialized if no instance exists,
        the GUI window is shown, `app.exec()` is called, and `app.quit()`
        is called upon exit.

        Args:
            mocker (MockerFixture): The pytest-mock fixture.
            app_context_fixture (AppContext): The mocked application context.
            mock_qapplication_class (MagicMock): The mocked QApplication class (constructor) provided by the fixture.
        """
        # The fixture `mock_qapplication_class` already patches QApplication.instance to return None.

        # Get the mock instance that QApplication() will return
        mock_app_instance = mock_qapplication_class.return_value
        mock_app_instance.exec.return_value = 0  # Ensure exec returns 0 for this test

        with pytest.raises(SystemExit):
            run(context=app_context_fixture)

        # Assert that the QApplication *constructor* was called
        mock_qapplication_class.assert_called_once_with(sys.argv)
        self.mock_window.show.assert_called_once()
        mock_app_instance.exec.assert_called_once()
        self.mock_window.close.assert_called_once()
        mock_app_instance.quit.assert_called_once()  # Should quit if it created the app

    def test_run_quits_app_when_created_new_qapp(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        mock_app_instance = mocker.Mock()
        mock_qapplication = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication.return_value = mock_app_instance
        mock_qapplication.instance.return_value = None

        mocker.patch("checkconnect.gui.gui_main.CheckConnectGUIRunner", side_effect=RuntimeError("GUI init failed"))

        with pytest.raises(SystemExit):
            run(context=app_context_fixture)

        mock_app_instance.quit.assert_called_once()

    def test_run_does_not_quit_when_existing_qapp(
        self, mocker: MockerFixture, app_context_fixture: AppContext, mock_qapplication_class: MagicMock
    ) -> None:
        mocker.patch("checkconnect.gui.gui_main.CheckConnectGUIRunner", side_effect=RuntimeError("GUI init failed"))

        with pytest.raises(SystemExit):
            run(context=app_context_fixture)

        mock_qapplication_class.quit.assert_not_called()

    def test_run_startup_error(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test `run` function's error handling during GUI startup.

        Simulates an error during `CheckConnectGUIRunner` initialization and
        verifies that the application exits with a non-zero code.

        Args:
            mocker (MockerFixture): The pytest-mock fixture.
            app_context_fixture (AppContext): The mocked application context.
            mock_qapplication_class (MagicMock): The mocked QApplication class (constructor).
        """
        mock_app_instance = mocker.Mock()
        mock_qapplication = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication.return_value = mock_app_instance
        mock_qapplication.instance.return_value = None

        # This patch should now correctly override the one in mock_qapplication_class
        # for this specific test, making QApplication.instance() return None.
        mocker.patch(
            "PySide6.QtWidgets.QApplication.instance",  # This must match the path in the fixture exactly
            return_value=None,
        )

        mocker.patch(
            "checkconnect.gui.gui_main.CheckConnectGUIRunner",
            side_effect=RuntimeError("GUI init failed"),
        )

        with pytest.raises(SystemExit) as excinfo:
            run(context=app_context_fixture, language="en")

        assert excinfo.value.code == 1

        mock_app_instance.exec.assert_not_called()
        mock_qapplication.show.assert_not_called()
        mock_qapplication.close.assert_not_called()
        mock_app_instance.quit.assert_called_once()

    def test_run_exec_error(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        mock_qapplication_class: MagicMock,
    ) -> None:
        """
        Test `run` function's error handling if `app.exec()` raises an exception.

        Simulates an error during the Qt event loop execution and verifies
        that the application exits with a non-zero code.

        Args:
            mocker (MockerFixture): The pytest-mock fixture.
            app_context_fixture (AppContext): The mocked application context.
            mock_qapplication_class (MagicMock): The mocked QApplication class (constructor).
        """

        # Arrange: make exec() raise an exception
        app_instance = mock_qapplication_class.return_value
        app_instance.exec.side_effect = RuntimeError("Qt exec failed")

        # Patch sys.exit so we can assert on it rather than letting it tear down pytest
        mock_exit = mocker.patch("checkconnect.gui.startup.sys.exit")

        # Act
        run(context=app_context_fixture, language="en")

        # Assert
        # 1) We did show the window
        self.mock_window.show.assert_called_once()

        # 2) exec() was called and raised
        app_instance.exec.assert_called_once()

        # 3) The window.close() path in finally ran
        self.mock_window.close.assert_called_once()

        # 4) Because we created the app, quit() was called
        app_instance.quit.assert_called_once()

        # 5) And we exited with code 1
        mock_exit.assert_called_once_with(1)

    def test_run_exit_code_propagation(
        self,
        app_context_fixture: AppContext,
        mock_qapplication_class: MagicMock,
    ) -> None:
        """
        Test that the exit code from `app.exec()` is propagated to `sys.exit()`.

        Verifies that if `app.exec()` returns a specific exit code (e.g., 42),
        `sys.exit()` is called with that same code.

        Args:
            mocker (MockerFixture): The pytest-mock fixture.
            app_context_fixture (AppContext): The mocked application context.
            mock_qapplication_class (MagicMock): The mocked QApplication class (constructor).
        """
        mock_app_instance = mock_qapplication_class.return_value
        mock_app_instance.exec.return_value = 42  # Simulate a custom exit code

        with pytest.raises(SystemExit) as excinfo:
            run(context=app_context_fixture, language="en")

        assert excinfo.value.code == 42

    def test_run_language_passed_to_setup_translations(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
        mock_qapplication_class: MagicMock,
    ) -> None:
        """
        Test that the `language` argument is correctly passed to `setup_translations`.

        Args:
            mocker (MockerFixture): The pytest-mock fixture.
            app_context_fixture (AppContext): The mocked application context.
            mock_qapplication_class (MagicMock): The mocked QApplication class (constructor).
        """
        mock_setup_translations = mocker.patch("checkconnect.gui.startup.setup_translations")

        with pytest.raises(SystemExit) as exc:
            run(context=app_context_fixture, language="fr")

        # optionally check the exit code was zero
        assert exc.value.code == 0

        # setup_translations receives the QApplication instance, not the class mock
        mock_setup_translations.assert_called_once_with(
            app=mock_qapplication_class.return_value,  # Pass the mock instance here
            context=app_context_fixture,
            language="fr",
        )
