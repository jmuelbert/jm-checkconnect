# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""Tests for the GUI entry point and startup logic."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PySide6.QtWidgets import QApplication

from checkconnect.config.appcontext import AppContext
from checkconnect.config.translation_manager import TranslationManager
from checkconnect.gui.gui_main import CheckConnectGUIRunner
from checkconnect.gui.startup import run, setup_translations

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture
    from structlog.typing import EventDict



class TestSetupTranslations:
    """Unit tests for the setup_translations function."""

    @pytest.mark.parametrize("language", ["en", "es", "de", "ko", "jp", "zh_CN"])
    def test_several_languages(
        self,
        app_context_fixture: AppContext,
        mock_qapplication_class: MagicMock,
        mocker: MockerFixture,
        language: str,
        caplog_structlog: list[EventDict],
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

        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        translator.load.return_value = True  # Simulate successful load from resource

        setup_translations(app=mock_qapplication_class, context=app_context_fixture, language=language)

        translation_file = f":/translations/{language}.qm"
        translator.load.assert_called_once_with(translation_file)

        assert any(
            record["event"] == "[mocked] Loaded Qt translations from Qt resource."
            and record["log_level"] == "debug"
            and record["path"] == translation_file
            for record in caplog_structlog
        )

    def test_without_language(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        caplog_structlog: list[EventDict],
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
            record["event"] == "[mocked] Qt preferred UI languages not found, falling back to system locale."
            and record["log_level"] == "warning"
            and record["language"] in ["en_US", "en"]
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "[mocked] Loaded Qt translations from Qt resource."
            and record["log_level"] == "debug"
            and record["path"] == ":/translations/en.qm"
            for record in caplog_structlog
        )

    def test_loads_from_resource(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        caplog_structlog: list[EventDict],
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
        translator = mocker.patch("checkconnect.gui.startup.QTranslator").return_value
        translator.load.return_value = True
        setup_translations(mock_qapplication_class, app_context_fixture, "en")
        translator.load.assert_called_once_with(":/translations/en.qm")
        mock_qapplication_class.installTranslator.assert_called_once_with(translator)

        assert any(
            record["event"] == "[mocked] Loaded Qt translations from Qt resource."
            and record["log_level"] == "debug"
            and record["path"] == ":/translations/en.qm"
            for record in caplog_structlog
        )

    def test_fallback_to_filesystem(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        tmp_path: Path,
        caplog_structlog: list[EventDict],
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
            record["event"] == "[mocked] Loaded Qt translations from file."
            and record["log_level"] == "debug"
            and record["path"] == str(file_path)
            for record in caplog_structlog
        )

    def test_load_fails_completely(
        self,
        app_context_fixture: AppContext,
        mocker: MockerFixture,
        mock_qapplication_class: MagicMock,
        tmp_path: Path,
        caplog_structlog: list[EventDict],
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
        assert any(
            record["event"] == "[mocked] No Qt translation found for language."
            and record["log_level"] == "warning"
            and record["language"] == "en"
            for record in caplog_structlog
        )


class TestRunFunction:
    """Unit tests for the `run` function, the main GUI entry point."""

    @pytest.fixture
    def app_context_fixture(self, mocker: MockerFixture):
        """
        Provides a mock application context.
        """
        mock_translator = mocker.Mock(spec=TranslationManager)
        mock_translator.gettext.side_effect = lambda text: f"[mocked] {text}"
        mock_translator.translate.side_effect = lambda text: f"[mocked] {text}"

        context = mocker.Mock(spec=AppContext)
        context.translator = mock_translator
        context.gettext = mock_translator.gettext
        context.translate = mock_translator.translate

        return context

    @pytest.fixture
    def setup_mocks(self, mocker: MockerFixture):
        """
        Provides a set of correctly configured mocks for testing the `run` function.

        This single fixture ensures a proper link between the mocks and the tested code.
        It replaces both the 'setup_mocks' and 'setup_run_mocks' fixtures.
        """
        # Patch the class names and configure their return values
        mock_app_instance = mocker.Mock(spec=QApplication)
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.return_value = mock_app_instance
        # Crucially, we mock QApplication.instance() to return None so that
        # `run` creates a new QApplication instance.
        mock_qapplication_class.instance.return_value = None

        mock_gui_runner_class = mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner"
        )
        # The CheckConnectGUIRunner mock will return a new MagicMock instance
        # when called, and that instance will have a 'main_window' attribute.
        mock_gui_runner = mock_gui_runner_class.return_value
        mock_window_instance = mock_gui_runner.main_window

        # Mock sys.exit to prevent the test from exiting prematurely
        mock_sys_exit = mocker.patch("checkconnect.gui.startup.sys.exit")

        # Mock setup_translations to prevent side effects
        mocker.patch("checkconnect.gui.startup.setup_translations")

        # Return a dictionary of the mocks for easy access in tests
        return {
            "app_instance": mock_app_instance,
            "window_instance": mock_window_instance,
            "sys_exit": mock_sys_exit
        }

    @pytest.fixture
    def mock_qapplication(self, mocker: MockerFixture):
        """
        Provides a mock QApplication instance.
        """
        mock_app_instance = mocker.Mock(spec=QApplication)
        # Patch the QApplication class itself
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.return_value = mock_app_instance
        mock_qapplication_class.instance.return_value = None

        mocker.patch("checkconnect.gui.startup.setup_translations")

        return mock_app_instance

    # Here starts the test cases
    def test_run_with_existing_qapplication_instance(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test the `run` function using a real QApplication instance provided by the
        q_app fixture.

        This test verifies the application lifecycle without mocking QApplication
        itself, which is the cause of the "QWidget: Must construct..." error.
        It ensures the CheckConnectGUIRunner is properly created, shown, and
        that the application runs and quits cleanly.

        Args:
            q_app (QApplication): The real QApplication instance provided by the fixture.
            mocker (MockerFixture): The pytest-mock fixture.
            app_context_fixture (AppContext): The mocked application context.
        """
        # ARRANGE
        # We no longer need to mock QApplication because the q_app fixture
        # provides a real one, which satisfies Qt's C++-level requirements.

        # Instead, we will mock the CheckConnectGUIRunner class to control its behavior
        # and prevent it from doing anything unexpected during the test.
        mock_runner_instance = mocker.MagicMock(spec=CheckConnectGUIRunner)
        mock_runner_class = mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner",
            return_value=mock_runner_instance
        )
        mocker.patch("checkconnect.gui.startup.setup_translations")

        # We need to explicitly mock sys.exit to prevent the app from
        # actually exiting the test runner when `app.exec()` is called.
        mocker.patch("sys.exit")

        # ACT
        # Execute the function under test. The `run` function will find the
        # real QApplication instance from the `q_app` fixture via QApplication.instance()
        # and use it.
        run(context=app_context_fixture)

        # ASSERT
        # Check that our mocks were called as expected.
        mock_runner_class.assert_called_once_with(context=app_context_fixture)
        mock_runner_instance.show.assert_called_once()
        # Note: We don't assert on app.exec() or app.quit() here because they are
        # part of the real QApplication and the mock on CheckConnectGUIRunner
        # is the focus. If you need to test the exec and quit, the first test
        # I provided is a better approach, but it requires addressing the
        # autouse fixture.

    def test_run_returns_one_on_gui_failure(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that the run function correctly returns None when an error occurs
        during GUI initialization.
        """
        # ARRANGE: Set up all the mocks to simulate the desired environment.
        # We will mock QApplication.instance() to return None first, forcing a new
        # QApplication instance to be created.
        mock_app_instance = mocker.Mock(spec=QApplication)
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.return_value = mock_app_instance
        mock_qapplication_class.instance.return_value = None

        # Patch the CheckConnectGUIRunner in the correct location (startup.py)
        # to raise a RuntimeError when it is initialized.
        mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner",
            side_effect=RuntimeError("GUI init failed")
        )

        # Patch setup_translations to prevent it from running.
        mocker.patch("checkconnect.gui.startup.setup_translations")

        # ACT: Call the run function and capture its return value.
        exit_code = run(context=app_context_fixture, language="en")

        # ASSERT: The function should return 1, as it currently does.
        assert exit_code == 1

        # We can also assert that the cleanup logic was executed as expected.
        # 1) The new QApplication was created.
        mock_qapplication_class.assert_called_once()

        # 2) The `app.quit()` method was called in the `finally` block,
        # since `created_new_app` was True.
        mock_app_instance.quit.assert_called_once()

    def test_run_returns_exit_code_on_gui_failure(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that the run function correctly returns an exit code of 1 when a
        RuntimeError occurs during GUI initialization.

        This test also asserts that the new QApplication instance's `quit` method
        is called in the `finally` block, as expected.
        """
        # ARRANGE: Set up all the mocks to simulate the desired environment.
        #

        # We'll mock QApplication.instance() to return None, forcing a new
        # QApplication instance to be created.
        mock_app_instance = mocker.Mock(spec=QApplication)
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.return_value = mock_app_instance
        mock_qapplication_class.instance.return_value = None

        # Patch the CheckConnectGUIRunner in the correct location (startup.py)
        # to raise a RuntimeError when it is initialized.
        mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner",
            side_effect=RuntimeError("GUI init failed")
        )

        # Patch setup_translations to prevent it from running.
        mocker.patch("checkconnect.gui.startup.setup_translations")

        # ACT: Call the run function and capture its return value.
        exit_code = run(context=app_context_fixture, language="en")

        # ASSERT: The function should return 1, as that is the intended exit code
        # for a failure, and the `quit` method on the newly created app should be called.
        assert exit_code == 1
        mock_app_instance.quit.assert_called_once()

    def test_run_does_not_quit_when_existing_qapp_is_found(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that the run function does NOT call app.quit() when it finds
        an existing QApplication instance.
        """
        # ARRANGE: Set up all the mocks to simulate the desired environment.

        # We will mock QApplication.instance() to return a pre-existing app mock.
        mock_existing_app = mocker.Mock(spec=QApplication)
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.instance.return_value = mock_existing_app

        # Patch the CheckConnectGUIRunner to ensure it does not raise an exception.
        mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner",
            return_value=mocker.Mock(spec=CheckConnectGUIRunner)
        )

        # Patch the app.exec() to prevent the main event loop from running indefinitely.
        mock_existing_app.exec.return_value = 0

        # Patch setup_translations to prevent it from running.
        mocker.patch("checkconnect.gui.startup.setup_translations")

        # ACT: Call the run function.
        exit_code = run(context=app_context_fixture, language="en")

        # ASSERT: The function should return the result of exec_(), which is 0.
        assert exit_code == 0

        # We must assert that the quit method was NOT called, because the
        # run function did not create the application itself.
        mock_existing_app.quit.assert_not_called()

    def test_run_exec_error(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test `run` function's error handling if `app.exec_()` raises an exception.
        """
        # ARRANGE: Set up all the mocks to simulate the desired environment.

        # We'll mock QApplication.instance() to return None, forcing a new
        # QApplication instance to be created.
        mock_app_instance = mocker.Mock(spec=QApplication)
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.return_value = mock_app_instance
        mock_qapplication_class.instance.return_value = None

        mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner",
            side_effect = RuntimeError("Mocked exec_ error")
        )

        # Patch setup_translations to prevent it from running.
        mocker.patch("checkconnect.gui.startup.setup_translations")

        # ACT: Call the run function and capture its return value.
        exit_code = run(context=app_context_fixture, language="en")

        # ASSERT: The function should return 1, as that is the intended exit code
        # for a failure, and the `quit` method on the newly created app should be called.
        assert exit_code == 1
        mock_app_instance.quit.assert_called_once()

    def test_run_window_lifecycle(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that the run function creates, shows, and eventually closes the window.
        """
        # ARRANGE
        # 1. Mock the app's 'exec' method so it doesn't block the test
        mock_exec = mocker.patch("PySide6.QtWidgets.QApplication.exec")

        # 2. Mock the CheckConnectGUIRunner class itself
        # This mock_window_class will be the "fake" CheckConnectGUIRunner class
        mock_window_class = mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner", autospec=True
        )

        # We can now get a reference to the mock instance that will be created
        # when the run function calls the mocked class.
        # We use `.return_value` to get the mock object that will be returned
        # when mock_window_class() is called.
        mock_window_instance = mock_window_class.return_value

        # ACT
        # Call the run function which should instantiate and show the window
        # We will assume a normal, successful run for this test.
        run(context=app_context_fixture, language="en")

        # ASSERT
        # 1. Assert that an instance of our mocked class was created.
        mock_window_class.assert_called_once()

        # 2. Assert that the 'show' method was called on the instance.
        mock_window_instance.show.assert_called_once()

        # 3. Assert that the 'close' method was called on the instance.
        # This would typically happen in a `finally` block or as part of cleanup.
        mock_window_instance.close.assert_called_once()

        # 4. Assert that the app's `exec` method was called.
        mock_exec.assert_called_once()

    def test_run_exit_code_propagation(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that the run function correctly propagates the exit code from QApplication.
        This version correctly handles the arguments passed to QApplication by mocking sys.argv.
        """
        # ARRANGE
        # 1. Patch the QApplication class where it is used.
        mock_qapplication_class = mocker.patch(
            "checkconnect.gui.startup.QApplication", autospec=True
        )

        # 2. Force the `run` function to create a new QApplication instance
        #    by mocking `.instance()` to return None.
        mock_qapplication_class.instance.return_value = None

        # 3. The `run` function will now call `QApplication()` and get this mock.
        mock_app_instance = mock_qapplication_class.return_value

        # 4. Set the return value on the `exec` method of this new mock instance.
        expected_exit_code = 42
        mock_app_instance.exec.return_value = expected_exit_code

        # 5. Mock the CheckConnectGUIRunner class to prevent a real window from being created.
        mock_window_class = mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner", autospec=True
        )
        mock_window_instance = mock_window_class.return_value

        # 6. CRITICAL CHANGE: Patch sys.argv with an empty list to control the arguments.
        # This prevents the QApplication constructor from seeing Pytest's arguments.
        mocker.patch.object(sys, 'argv', [])

        # ACT
        returned_exit_code = run(context=app_context_fixture, language="en")

        # ASSERT
        # Assert that the new QApplication instance was created with the arguments we mocked.
        mock_qapplication_class.assert_called_once_with([])

        # Assert that a window instance was created and shown.
        mock_window_class.assert_called_once()
        mock_window_instance.show.assert_called_once()

        # Assert that the `exec` method was called.
        mock_app_instance.exec.assert_called_once()

        # Assert that the function correctly returned the exit code we set.
        assert returned_exit_code == expected_exit_code

        # Assert that cleanup methods were called.
        mock_window_instance.close.assert_called_once()
        mock_app_instance.quit.assert_called_once()

    def test_run_language_passed_to_setup_translations(
        self,
        mocker: MockerFixture,
        app_context_fixture: AppContext,
    ) -> None:
        """
        Test that the `language` argument is correctly passed to `setup_translations`
        when a new QApplication instance is created.
        """
        # ARRANGE: Set up all the mocks to simulate the desired environment.
        # Patch setup_translations to verify it's called with the correct arguments.
        mock_setup_translations = mocker.patch("checkconnect.gui.startup.setup_translations")

        # We need to mock QApplication.instance() to return None so that
        # `run` creates a new QApplication instance.
        mock_app_instance = mocker.Mock(spec=QApplication)
        mock_qapplication_class = mocker.patch("checkconnect.gui.startup.QApplication")
        mock_qapplication_class.return_value = mock_app_instance
        mock_qapplication_class.instance.return_value = None

        # Mock the GUI runner to prevent it from creating a real window.
        mocker.patch(
            "checkconnect.gui.startup.CheckConnectGUIRunner",
            return_value=mocker.Mock(spec=CheckConnectGUIRunner)
        )

        # CRITICAL FIX: Ensure the mocked exec_() method returns a specific integer.
        # This prevents the test from hanging and provides a value to assert against.
        mock_app_instance.exec.return_value = 0

        # ACT: Call the run function with a specific language.
        exit_code = run(context=app_context_fixture, language="fr")

        # ASSERT: Verify that the exit code is what we expect from the mock.
        assert exit_code == 0

        # Verify that `setup_translations` was called exactly once with the correct arguments.
        mock_setup_translations.assert_called_once_with(
            app=mock_app_instance,
            context=app_context_fixture,
            language="fr",
        )
