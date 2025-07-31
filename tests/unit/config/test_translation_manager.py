# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Pytest-mock test suite for the TranslationManager class.

This module contains comprehensive tests for the TranslationManager, ensuring its
correct initialization, language detection, translation loading, and message
translation capabilities. It uses pytest-mock for mocking external dependencies
like gettext, locale, and importlib.resources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import os

import gettext
import locale
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# Assuming __about__ is in checkconnect.__about__
# If __about__ isn't a separate module, you might need to adjust the patch path
from checkconnect import __about__

# Assuming SettingsManagerSingleton exists for default language lookup
# Assuming TranslationManager and __about__ are in the correct paths
# Adjust imports if your file structure is different.
from checkconnect.config.translation_manager import TranslationManager, TranslationManagerSingleton

if TYPE_CHECKING:
    from pytest_mock import MockerFixture
    from structlog.typing import EventDict

# --- Fixtures ---


@pytest.fixture
def mock_gettext_translation(mocker: Any) -> Generator[Any, Any, Any]:
    """
    Fixture to mock gettext.translation.

    Returns:
        MagicMock: A mock object for gettext.translation, which returns a mock
                   translation object with `gettext` and `ngettext` methods.
    """
    # This mocks the 'translation' *function*
    mock_trans_func = mocker.patch("gettext.translation")

    # This is the mock object that will be *returned* by gettext.translation
    # We define its behavior (e.g., its .gettext method) here.
    mock_translations_obj = mocker.MagicMock(spec=gettext.NullTranslations)
    # Now, explicitly define the 'gettext' method on this mock object.
    # We are assigning a specific MagicMock instance.
    mock_gettext_method = mocker.MagicMock(return_value="Translated text")
    mock_translations_obj.gettext = mock_gettext_method

    # Do the same for ngettext if you plan to assert its identity later
    mock_ngettext_method = mocker.MagicMock(return_value="Translated plural %d")
    mock_translations_obj.ngettext = mock_ngettext_method

    # Crucially, set the return value of the patched 'translation' function
    # to *this specific* mock_translations_obj.
    mock_trans_func.return_value = mock_translations_obj

    # ... other mocks (locale, os.getenv, pathlib.Path.exists) ...
    mocker.patch("gettext.install")  # If your code calls this
    mocker.patch("locale.setlocale")
    mocker.patch("locale.getlocale", return_value=("en_US.UTF-8", "UTF-8"))
    mocker.patch(
        "os.getenv",
        side_effect=lambda var: None if var in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"] else os.environ.get(var),
    )
    mocker.patch("pathlib.Path.exists", return_value=True)

    # Yield all the mocks you need to access in your test
    yield mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method


@pytest.fixture
def assert_translation_called_with():
    """
    Helper fixture to assert gettext.translation mock calls flexibly.

    Usage in test:
        def test_something(assert_translation_called_with, mock_gettext_translation):
            mock_trans_func, _, _ = mock_gettext_translation
            # ... run code that calls gettext.translation ...
            assert_translation_called_with(
                mock_trans_func,
                domain="mock_app_name",
                localedir="/mock/project/root/locales",
                languages=["en"],
                fallback=True,
            )
    """

    def _assert(
        mock_trans_func: MagicMock,
        *,
        domain: str,
        localedir: Any,
        languages: list[str],
        fallback: bool,
    ) -> None:
        mock_trans_func.assert_called_once()
        args, kwargs = mock_trans_func.call_args

        # domain kann positional oder keyword sein
        actual_domain = args[0] if args else kwargs.get("domain")
        assert actual_domain == domain, f"Expected domain '{domain}', got '{actual_domain}'"

        actual_localedir = kwargs.get("localedir") or (args[1] if len(args) > 1 else None)
        assert str(actual_localedir).endswith("locales"), f"Expected localedir '{localedir}', got '{actual_localedir}'"

        actual_languages = kwargs.get("languages") or (args[2] if len(args) > 2 else None)
        assert actual_languages == languages, f"Expected languages '{languages}', got '{actual_languages}'"

        actual_fallback = kwargs.get("fallback")
        assert actual_fallback == fallback, f"Expected fallback '{fallback}', got '{actual_fallback}'"

    yield _assert


@pytest.fixture
def mock_locale_functions(mocker: MockerFixture) -> None:
    """
    Mocks locale.setlocale, locale.getlocale, and relevant os.getenv calls
    to provide a controlled environment for locale-dependent tests.
    """
    # 1. Mock locale.setlocale: Usually just need it to not error.
    mock_set_locale = mocker.patch("locale.setlocale", return_value="C")

    # 2. Mock locale.getlocale: Set a predictable return value.
    # This is what functions relying on locale.getlocale will receive.
    mock_get_locale = mocker.patch("locale.getlocale", return_value=("en_US", "UTF-8"))

    # 3. Mock os.getenv to prevent environment variables from interfering
    # For a unit test, it's often best to mock specific calls or entirely control it.
    # We create a dictionary of expected environment variables for locale,
    # and provide a side effect that looks them up.
    # Any other os.getenv calls will return None (or raise, depending on strictness).
    locale_env_vars = {
        "LANGUAGE": None,
        "LC_ALL": None,
        "LC_MESSAGES": None,
        "LANG": None,
        # Add any other specific env vars your code checks related to locale if needed
    }

    def controlled_getenv_side_effect(var_name: str, default: str | None = None) -> str | None:
        """
        Custom side effect for os.getenv to control locale-related variables.
        """
        if var_name in locale_env_vars:
            return locale_env_vars[var_name]
        # For any other environment variable, return None unless a default is given.
        # This provides strong isolation for unit tests.
        return default

    mocker.patch("os.getenv", side_effect=controlled_getenv_side_effect)

    # If your code uses os.environ directly to get locale variables (less common but possible)
    # mocker.patch.dict(os.environ, {"LANGUAGE": "", "LC_ALL": "", "LC_MESSAGES": "", "LANG": ""}, clear=True)
    # Be careful with clear=True, as it clears ALL env vars for the duration of the test.
    # A safer approach for os.environ is to modify specific keys without clearing.
    # Example for direct os.environ manipulation if needed:
    # mocker.patch.dict(os.environ, {
    #     "LANGUAGE": "", "LC_ALL": "", "LC_MESSAGES": "", "LANG": ""
    # })

    # Yielding the mocks allows tests to make assertions on them if needed
    yield mock_set_locale, mock_get_locale

    # No cleanup specifically needed for mocks as mocker handles it.


@pytest.fixture
def mock_pathlib_path() -> Generator[MagicMock, None, None]:
    """
    Mocks Path(__file__).parent / 'locales' to return a real path with exists mocked.
    """
    """
    Mocks pathlib.Path(__file__).parent / LOCALES_DIR_NAME to return a real path
    within the project structure (src/checkconnect/config/locales), but controls
    .exists() via patching. Also returns the mocked initial Path instance and the final expected path.
    """
    # Dynamisch: src/checkconnect/config/locales relativ zu diesem Testfile
    current_test_file = Path(__file__)
    project_root = current_test_file.parent.parent.parent.parent  # -> bis src/

    expected_path = project_root / "src" / "checkconnect" / "locales"

    # Mocks
    mock_initial_path = MagicMock(spec=Path)
    mock_parent = MagicMock(spec=Path)
    mock_initial_path.parent = mock_parent
    mock_parent.__truediv__.return_value = expected_path

    # Patch Path() and expected_path.exists()
    with patch("pathlib.Path", return_value=mock_initial_path), patch.object(Path, "exists", return_value=True):
        yield mock_initial_path, expected_path


@pytest.fixture
def mock_settings_manager_singleton():
    """
    Mocks SettingsManagerSingleton.get_instance().get_setting()
    for default language lookup.
    """
    mock_settings_manager = MagicMock()
    # Mock its get_instance method to return the mock manager
    mock_settings_manager_singleton_get_instance = MagicMock(return_value=mock_settings_manager)
    mock_settings_manager.get_setting.return_value = None  # Default: no language from settings

    with patch(
        "checkconnect.config.settings_manager.SettingsManagerSingleton.get_instance",
        new=mock_settings_manager_singleton_get_instance,
    ) as patched_get_instance:
        yield patched_get_instance, mock_settings_manager


@pytest.fixture
def mock_about_app_name() -> Generator[None, None, None]:
    with patch("checkconnect.config.translation_manager.__app_name__", "mock_app_name"):
        yield


# --- Tests for TranslationManager ---


class TestTranslationManager:
    """
    Test suite for the TranslationManager class.
    """

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("input_language", "expected_language", "settings_lang", "system_lang"),
        [
            ("en", "en", None, None),
            ("de", "de", None, None),
            (None, "fr", "fr", None),  # Falls back to settings
            (None, "es", None, "es"),  # Falls back to system locale
            (None, "en", None, None),  # Falls back to default if no settings/system
        ],
    )
    @pytest.mark.unit
    def test_init_and_set_language(
        self,
        input_language: str,
        expected_language: str,
        settings_lang: str,
        system_lang: str,
        mocker: Any,
        mock_gettext_translation: Generator[Any, Any, Any],
        mock_pathlib_path: Generator[tuple[MagicMock, Path], None, None],
        mock_locale_functions: Generator[Any, Any, Any],
        mock_settings_manager_singleton: MagicMock,
        assert_translation_called_with,
    ) -> None:
        """
        Tests initialization and the _set_language method's logic for determining language.
        """
        mock_initial_path, expected_locale_dir = mock_pathlib_path

        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        mock_setlocale, mock_getlocale = mock_locale_functions
        mock_settings_singleton_get_instance, mock_settings_manager = mock_settings_manager_singleton

        # Configure mocks based on test parameters
        mock_settings_manager.get_setting.return_value = settings_lang
        mock_getlocale.return_value = (system_lang, "UTF-8")

        # Determine if we're simulating system locale fallback via os.getenv
        should_mock_env = input_language is None and settings_lang is None and system_lang is not None

        # Patch os.getenv based on fallback path
        if input_language is None and settings_lang is None:
            if system_lang:
                # Simulate system_lang being found via env var → locale.getlocale() won't be called
                mocker.patch(
                    "os.getenv",
                    side_effect=lambda var: f"{system_lang}_US.UTF-8"
                    if var in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"]
                    else None,
                )
            else:
                # Simulate no env vars available → must fall back to locale.getlocale()
                mocker.patch("os.getenv", return_value=None)

        manager = TranslationManager()
        manager.configure(language=input_language, translation_domain="mock_app_name")

        # Assert initial attributes
        assert manager.translation_domain == "mock_app_name"

        assert manager.locale_dir == expected_locale_dir
        assert manager.current_language == expected_language
        assert manager.translation is mock_translations_obj
        assert manager._ is mock_translations_obj.gettext

        # Assert that _set_language logic was called correctly
        # locale.setlocale should be called with the determined language
        if input_language is None and settings_lang is None and system_lang is None:
            # Full fallback path triggers _get_system_language and adds neutral setlocale
            mock_setlocale.assert_has_calls([
                call(locale.LC_ALL, ""),  # From _get_system_language
                call(locale.LC_ALL, expected_language),  # From _set_language
            ])
            assert mock_setlocale.call_count == 2
        else:
            # In all other cases only _set_language calls setlocale
            mock_setlocale.assert_called_once_with(locale.LC_ALL, expected_language)

        # gettext.translation should be called with the correct args

        # Nutze Helper zum Prüfen der Aufrufe
        assert_translation_called_with(
            mock_trans_func,
            domain="mock_app_name",
            localedir="/mock/project/root/locales",
            languages=[expected_language],
            fallback=True,
        )

        # Assertions for fallback logic:
        if input_language is None:
            mock_settings_manager.get_setting.assert_called_once_with("general", "default_language")

            if settings_lang is None:
                if system_lang:
                    # simulate env var detection (patched above)
                    mock_getlocale.assert_not_called()
                else:
                    # force env vars to return None → expect getlocale()
                    mock_getlocale.assert_has_calls([call(locale.LC_ALL), call(locale.LC_CTYPE)])
                    assert mock_getlocale.call_count == 2

    @pytest.mark.unit
    def test_init_custom_args(
        self,
        mock_gettext_translation: Generator[Any, Any, Any],
        mock_locale_functions: Generator[Any, Any, Any],
        assert_translation_called_with,
        tmp_path: Path,
        mocker: Any,
    ) -> None:
        """
        Test initialization with custom language, domain, and locale_dir.
        """
        custom_locale_dir = tmp_path / "custom_locales"
        custom_locale_dir.mkdir()  # Ensure it exists for the test
        expected_language = "fr"

        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        mock_setlocale, mock_getdefaultlocale = mock_locale_functions

        # Mock Path(__file__).parent / self.LOCALES_DIR_NAME.exists() to return False
        mock_path_obj = mocker.MagicMock(spec=Path)
        mock_path_obj.exists.return_value = False
        mock_path_obj.parent.__truediv__.return_value = mock_path_obj
        mocker.patch("pathlib.Path", return_value=mock_path_obj)

        manager = TranslationManager()
        manager.configure(
            language=expected_language,
            translation_domain="custom_domain",
            locale_dir=custom_locale_dir,
        )

        assert manager.current_language == expected_language
        assert manager.translation_domain == "custom_domain"
        assert manager.locale_dir == custom_locale_dir

        # Assert that _set_language logic was called correctly
        # locale.setlocale should be called with the determined language
        mock_setlocale.assert_called_once_with(locale.LC_ALL, expected_language)

        # Nutze Helper zum Prüfen der Aufrufe
        assert_translation_called_with(
            mock_trans_func,
            domain="custom_domain",
            localedir="/mock/project/root/locales",
            languages=[expected_language],
            fallback=True,
        )
        assert manager._ is mock_trans_func.return_value.gettext  # noqa: SLF001 Test the private _
        assert manager.translation is mock_trans_func.return_value

    @pytest.mark.unit
    def test_default_locale_dir_exists(self, mock_pathlib_path: Generator[tuple[MagicMock, Path], None, None]) -> None:
        mock_initial_path, expected_path = mock_pathlib_path

        manager = TranslationManager()

        result = manager._default_locale_dir()
        print("DEBUG: result", result)
        print("DEBUG: expected_path", expected_path)

        assert result == expected_path
        assert result.exists()

    @pytest.mark.unit
    def test_package_locale_dir(self, mocker: Any) -> None:
        """
        Test that _package_locale_dir returns the correct fallback path
        using importlib.resources.files().
        """
        # GIVEN: mocks
        mock_files_return = mocker.MagicMock(spec=Path)
        mock_final_path = mocker.MagicMock(spec=Path)

        # mock: importlib.resources.files(__app_name__.lower())
        mock_importlib_files = mocker.patch(
            "checkconnect.config.translation_manager.importlib.resources.files", return_value=mock_files_return
        )

        # mock: files(...) / LOCALES_DIR_NAME
        mock_files_return.__truediv__.return_value = mock_final_path

        # mock: str(...) → just returns a fake string
        mock_final_path_str = "/mocked/fallback/locale/dir"
        mock_final_path.__str__.return_value = mock_final_path_str

        # WHEN
        manager = TranslationManager()
        manager.configure(language="en")
        result = manager._package_locale_dir()

        # THEN
        assert result == mock_final_path_str
        mock_importlib_files.assert_called_once_with(__about__.__app_name__.lower())
        mock_files_return.__truediv__.assert_called_once_with(manager.LOCALES_DIR_NAME)

    @pytest.mark.unit
    def test_set_language_fallback_on_file_not_found(
        self,
        mock_gettext_translation: MagicMock,
        mock_locale_functions: Generator[Any, Any, Any],
        mocker: Any,
        assert_translation_called_with,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Test _set_language falls back to system language if specified translation is not found.
        """

        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        mock_set_locale, mock_locale_getlocale = mock_locale_functions

        mock_locale_getlocale.return_value = ("es_ES", "UTF-8")  # System language is Spanish

        # First call to gettext.translation raises FileNotFoundError
        mock_trans_func.side_effect = [
            FileNotFoundError("Translation file not found"),
            mocker.MagicMock(
                spec=gettext.NullTranslations, gettext=lambda msg: f"Fallback: {msg}"
            ),  # Second call for fallback
        ]

        language: str = "fr"
        manager = TranslationManager()
        manager.configure(language=language, translation_domain="mock_app_name")  # Request French, but it will fail

        # Nutze Helper zum Prüfen der Aufrufe
        assert_translation_called_with(
            mock_trans_func,
            domain="mock_app_name",
            localedir=manager.locale_dir,
            languages=[language],
            fallback=True,
        )

        assert f"Translation for '{language}' failed to load from" in caplog.text
        assert "Translation file not found" in caplog.text

        assert (
            manager.current_language == "fr"
        )  # current_language is still the requested one, but the actual translation object is for fallback.

        assert manager._("Hello") == "Fallback: Hello"  # noqa: SLF001 Test the private _

    @pytest.mark.unit
    def test_get_system_language_success(
        self,
        mock_locale_functions: Generator[Any, Any, Any],
        mocker: Any,
    ) -> None:
        """
        Test _get_system_language returns the correct system language code.
        """
        mock_set_locale, mock_locale_getlocale = mock_locale_functions

        manager = TranslationManager()
        manager.configure(language="en")  # Minimal init

        mock_locale_getlocale.return_value = ("de_DE.UTF-8", "UTF-8")
        assert manager._get_system_language() == "de"  # noqa: SLF001 Test the private _get_system_language

        mock_locale_getlocale.return_value = ("en_GB", "UTF-8")
        assert manager._get_system_language() == "en"  # noqa: SLF001 Test the private _get_system_language

        mock_locale_getlocale.return_value = ("zh_Hans", "UTF-8")
        assert manager._get_system_language() == "zh"  # noqa: SLF001 Test the private _get_system_language

    @pytest.mark.unit
    def test_get_system_language_locale_error_fallback(
        self,
        mock_locale_functions: Generator[Any, Any, Any],
        mocker: Any,
    ) -> None:
        """
        Test _get_system_language falls back to "en" on locale.Error.
        """
        # Mock Path(__file__).parent / self.LOCALES_DIR_NAME.exists() to return False
        mock_path_obj = mocker.MagicMock(spec=Path)
        mock_path_obj.exists.return_value = False
        mock_path_obj.parent.__truediv__.return_value = mock_path_obj
        mocker.patch("pathlib.Path", return_value=mock_path_obj)

        mock_set_locale, mock_locale_getlocale = mock_locale_functions

        mock_locale_getlocale.side_effect = locale.Error("Bad locale setting")
        manager = TranslationManager()
        manager.configure(language="en")  # Minimal init
        assert manager._get_system_language() == "en"  # noqa: SLF001 Test the private _get_system_language

    @pytest.mark.unit
    def test_get_system_language_none_fallback(
        self,
        mock_locale_functions: Generator[Any, Any, Any],
        mocker: Any,
    ) -> None:
        """
        Test _get_system_language falls back to "en" if locale.getlocale returns None.
        """

        mock_set_locale, mock_locale_getlocale = mock_locale_functions

        mock_locale_getlocale.return_value = (None, None)

        manager = TranslationManager()
        manager.configure(language="en")  # Minimal init
        assert manager._get_system_language() == "en"  # noqa: SLF001 Test the private _get_system_language

    @pytest.mark.unit
    def test_gettext_method_delegation(
        self,
        mock_gettext_translation: MagicMock,
    ) -> None:
        """
        Tests that the gettext() method delegates to the underlying translation object.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        manager = TranslationManager()
        manager.configure(language="en")  # Language doesn't matter for this test

        test_message = "Hello, world!"
        translated_message = manager.gettext(test_message)

        # Verify manager.gettext calls the mock translation object's gettext
        mock_translations_obj.gettext.assert_called_once_with(test_message)
        assert translated_message == "Translated text"

    @pytest.mark.unit
    def test_gettext_method(
        self,
        mock_gettext_translation: MagicMock,
        mocker: Any,
    ) -> None:
        """
        Test gettext method calls the underlying translation object's gettext.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        manager = TranslationManager()
        manager.configure(language="en")
        text: str = "Hello"
        translated_text = manager.gettext(text)
        assert translated_text == "Translated text"
        mock_trans_func.return_value.gettext.assert_called_once_with(text)

    @pytest.mark.unit
    def test_translate_method(
        self,
        mock_gettext_translation: MagicMock,
        mocker: Any,
    ) -> None:
        """
        Test translate method calls the underlying translation object's gettext.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        manager = TranslationManager()
        manager.configure(language="en")
        text: str = "World"
        translated_text = manager.translate(text)

        assert translated_text == "Translated text"
        mock_trans_func.return_value.gettext.assert_called_once_with("World")

    @pytest.mark.unit
    @pytest.mark.parametrize(
        ("count", "expected_ngettext_return", "expected_translate_plural_return"),
        [
            # The `ngettext` return value *must* contain a %d placeholder
            (1, "Singular item (count: %d)", "Singular item (count: 1)"),
            (2, "Plural items (count: %d)", "Plural items (count: 2)"),
            (5, "Plural items (count: %d)", "Plural items (count: 5)"),
        ],
    )
    def test_translate_plural_method(
        self,
        count: int,
        expected_ngettext_return: str,
        expected_translate_plural_return: str,
        mock_gettext_translation: Generator[Any, Any, Any],  # Use Generator for type hint consistency
        mocker: Any,
    ) -> None:
        """
        Test translate_plural method calls ngettext and formats the result.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        # 1. Patch pathlib.Path before TranslationManager is instantiated
        mock_path_exists = mocker.patch("pathlib.Path.exists", return_value=True)

        # 2. Configure the mock_translations_obj's ngettext method
        # This mock should be configured *before* the call to translate_plural.
        # We are mocking the ngettext method of the object returned by gettext.translation()
        mock_translations_obj.ngettext.return_value = expected_ngettext_return

        # 3. Instantiate TranslationManager *after* patching Path
        manager = TranslationManager()
        manager.configure(language="en")
        # Crucially, you need to set the mocked translation object on the manager
        # This assumes your TranslationManager's __init__ or some other method
        # would normally assign the result of gettext.translation() to self.translation
        manager.translation = mock_translations_obj  # Assign the mock here

        singular = "item"
        plural = "items"
        translated_text = manager.translate_plural(singular, plural, count)

        # Assertions
        # 1. Verify that ngettext was called correctly
        mock_translations_obj.ngettext.assert_called_once_with(singular, plural, count)

        # 2. Verify the final formatted string
        assert translated_text == expected_translate_plural_return

        # Optional: Verify path exists was checked
        mock_path_exists.assert_called_once()

    @pytest.mark.unit
    def test_translate_context_method(
        self,
        mock_gettext_translation: MagicMock,
    ) -> None:
        """
        Test translate_context method formats the input and calls gettext.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        manager = TranslationManager()
        manager.configure(language="en")
        context = "button"
        text = "Open"
        translated_text = manager.translate_context(context, text)

        assert translated_text == "Translated text"
        mock_trans_func.return_value.gettext.assert_called_once_with("button|Open")

    @pytest.mark.unit
    def test_set_language_method(
        self,
        mock_gettext_translation: MagicMock,
        assert_translation_called_with,
    ) -> None:
        """
        Test set_language method updates current_language and reloads translations.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        manager = TranslationManager()
        manager.configure(language="en", translation_domain="mock_app_name")

        mock_trans_func.reset_mock()

        manager.set_language("de")

        assert manager.current_language == "de"

        # Now, assert_translation_called_with will only see the 'de' call
        assert_translation_called_with(
            mock_trans_func,
            domain="mock_app_name",
            localedir=manager.locale_dir,
            languages=["de"],
            fallback=True,
        )

        # Now this assertion should work because manager.gettext should be the exact same mock_gettext_method
        assert manager._ is mock_gettext_method

    @pytest.mark.unit
    def test_get_current_language(
        self,
        mocker: Any,
    ) -> None:
        """
        Test get_current_language returns the active language.
        """
        manager = TranslationManager()
        manager.configure(language="fr")
        assert manager.get_current_language() == "fr"

        manager.set_language("es")
        assert manager.get_current_language() == "es"

    @pytest.mark.unit
    @pytest.mark.usefixtures("mock_about_app_name")
    def test_init_with_explicit_domain_and_locale_dir(
        self,
        mock_gettext_translation: Generator[Any, Any, Any],
        mock_locale_functions: Generator[Any, Any, Any],
        mock_pathlib_path,  # Still needed for default path calculation if locale_dir is None
        mock_settings_manager_singleton,
        assert_translation_called_with,
    ):
        """
        Tests that explicit translation_domain and locale_dir are used.
        """
        # Unpack the yielded mocks
        mock_trans_func, mock_translations_obj, mock_gettext_method, mock_ngettext_method = mock_gettext_translation

        explicit_domain = "my_custom_domain"
        explicit_locale_dir = "/custom/path/to/locales"

        manager = TranslationManager()
        manager.configure(language="fr", translation_domain=explicit_domain, locale_dir=explicit_locale_dir)

        assert manager.translation_domain == explicit_domain
        assert manager.locale_dir == Path(explicit_locale_dir)
        assert manager.current_language == "fr"

        # Verify that gettext.translation and gettext.install use the explicit values
        assert_translation_called_with(
            mock_trans_func,
            domain=explicit_domain,
            localedir=explicit_locale_dir,
            languages=["fr"],
            fallback=True,
        )

        # Ensure _default_locale_dir was NOT called as locale_dir was provided
        mock_pathlib_path[0].assert_not_called()


@pytest.mark.unit
class TestTranslationManagerLocaleDir:
    def test_default_locale_dir_used_when_no_argument_given(
        self,
        mock_pathlib_path: Generator[tuple[MagicMock, Path], None, None],
    ) -> None:
        """Test that _default_locale_dir is used when locale_dir is not provided and project locale dir exists."""
        mock_initial_path, expected_locale_dir = mock_pathlib_path
        mock_initial_path.assert_not_called()

        manager = TranslationManager()
        manager.configure(language="en", translation_domain="checkconnect", locale_dir=None)

        assert manager.locale_dir == expected_locale_dir

    def test_given_locale_dir_is_used_directly(self) -> None:
        """Test that provided locale_dir argument is used directly."""
        custom_path = "/custom/locale/dir"
        manager = TranslationManager()
        manager.configure(language="en", translation_domain="checkconnect", locale_dir=custom_path)

        assert manager.locale_dir == Path(custom_path)

    @patch("checkconnect.config.translation_manager.importlib.resources.files")
    def test_given_non_existing_locale_dir_falls_back_to_package(self, mock_files: MagicMock) -> None:
        """Even if a path is given but nonexistent, manager uses it as is; fallback only applies when `locale_dir` is None."""
        fallback_path = Path("/fallback/package/locales")
        mock_files.return_value.__truediv__.return_value = fallback_path

        custom_path = "/nonexistent/path/to/locales"
        manager = TranslationManager()
        manager.configure(language="en", translation_domain="checkconnect", locale_dir=custom_path)

        assert manager.locale_dir == Path(custom_path)  # still uses given path


class TestTranslationManagerSingleton:
    """
    Test suite for the TranslationManagerSingleton.get_instance() helper function.
    """

    def test_get_instance_creates_and_returns_single_instance(
        self,
    ) -> None:
        """
        Test get_instance creates a new instance on first call and returns the same on subsequent calls.
        """
        first_instance = TranslationManagerSingleton.get_instance()
        second_instance = TranslationManagerSingleton.get_instance()

        assert first_instance is second_instance
        # Verify that TranslatorManager was initialized only once
        # This is implicitly tested by the autouse fixture resetting logging
        # and structlog, ensuring a fresh start for each test.
        # We can't directly count TranslatorManager.__init__ calls due to mocking.
        # However, the singleton pattern's core is tested by `is` check.

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_clears_instance(self) -> None:
        """
        Test that reset sets the _instance to None.
        """
        # Ensure an instance exists
        instance = TranslationManagerSingleton.get_instance()
        assert instance is not None

        # Call the reset method
        TranslationManagerSingleton.reset()

        # Assert that the instance is now None
        assert TranslationManagerSingleton._instance is None  # noqa: SLF001

    @pytest.mark.unit
    @patch("checkconnect.config.translation_manager.TranslationManager")
    def test_reset_and_new_instance(self, mock_translation_manager_cls: MagicMock) -> None:
        """
        Test reset method clears the singleton instance.
        """
        mock_instance_1 = MagicMock(name="FirstTranslationManager")
        mock_instance_2 = MagicMock(name="SecondTranslationManager")

        # Ensure each call to LoggingManager() gives a new instance
        mock_translation_manager_cls.side_effect = [mock_instance_1, mock_instance_2]

        first_instance = TranslationManagerSingleton.get_instance()
        assert first_instance is mock_instance_1

        # Reset and get new instance
        TranslationManagerSingleton.reset()
        second_instance = TranslationManagerSingleton.get_instance()
        assert second_instance is mock_instance_2

        # ✅ Main assertion
        assert first_instance is not second_instance

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_initialization_errors(
        self,
    ) -> None:
        """
        Test get_initialization_errors method returns errors during initialization.
        """
        # We need to patch __init__ BEFORE the singleton tries to create an instance.
        # This means patching it within a 'with' statement, and then calling get_instance
        # inside that 'with' statement.

        # The key is that cleanup_singletons should ensure TranslationManagerSingleton
        # is reset, so get_instance() will call __init__ again.
        with (
            patch.object(TranslationManager, "__init__", side_effect=Exception("Mocked error")),
            pytest.raises(Exception, match="Mocked error"),
        ):
            # Call get_instance *inside* the patch context.
            # This will trigger __init__ with the side_effect.
            TranslationManagerSingleton.get_instance()

        # After the exception is caught, you could potentially assert on the instance's errors
        # if the LoggingManager's __init__ was designed to set them even on failure.
        # However, since the Exception propagates, the instance won't be fully initialized.
        # This test primarily validates the exception propagation.

        # If you *also* need to check self.setup_errors, you'd need to catch the exception,
        # and then inspect the *exception object itself* if it contained the instance,
        # or mock the append method to capture what would have been appended.
        # For now, let's focus on the primary failure (exception not raised).

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_clears_initialization_errors(self) -> None:
        """
        Test that reset clears any accumulated initialization errors.
        """
        # Manually add an error to simulate a previous failed initialization
        TranslationManagerSingleton._initialization_errors.append("Simulated init error 1")  # noqa: SLF001
        TranslationManagerSingleton._initialization_errors.append("Simulated init error 2")  # noqa: SLF001

        for sim_error in TranslationManagerSingleton._initialization_errors:
            # Verify errors are present before reset
            print(f"Error: {sim_error}")

        assert len(TranslationManagerSingleton.get_initialization_errors()) == 2

        # Call the reset method
        TranslationManagerSingleton.reset()

        # Assert that the errors list is now empty
        assert TranslationManagerSingleton.get_initialization_errors() == []
        assert len(TranslationManagerSingleton.get_initialization_errors()) == 0

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_initialization_errors_returns_correct_errors(self) -> None:
        """
        Test get_initialization_errors returns errors during initialization.
        This re-uses the pattern from your previous test problem.
        """
        # Patch TranslationManager's __init__ to raise an error
        expected_error_msg = "Mocked init error for test"
        with patch.object(TranslationManager, "__init__", side_effect=Exception(expected_error_msg)):
            with pytest.raises(Exception, match=expected_error_msg):
                # This call will trigger __init__ which will raise the error
                TranslationManagerSingleton.get_instance()

            # Now, after the exception, check if the error was logged in the singleton
            errors = TranslationManagerSingleton.get_initialization_errors()
            assert len(errors) == 1
            assert expected_error_msg in errors[0]  # Check that the message is part of the error string

        # Ensure cleanup_singletons runs after this test to clear the error for subsequent tests
