# SPDX-License-Identifier: EUPL-1.2

# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
translation.py — TranslationManager for internationalization.

This module provides the TranslationManager class, which handles loading and
managing gettext-based translations for the CheckConnect project. It attempts
to use language preferences from a configuration file or system locale, and
falls back to English if no translation files are found.

Typical usage:
--------------
>>> tm = TranslationManager(language="de")
>>> print(tm.gettext("Hello"))

The TranslationManager automatically falls back to default translation
files if the specified ones are missing.
"""

from __future__ import annotations

import gettext
import importlib.resources
import locale
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, Final

from checkconnect.__about__ import __app_name__
from checkconnect.config.settings_manager import SettingsManagerSingleton

logger = logging.getLogger(__name__)


class TranslationManager:
    """
    Manage translations for the CheckConnect project.

    This class initializes and manages gettext-based translation files (.mo)
    for multiple languages, based on project domain, language code, and locale
    directory.

    Attributes
    ----------
    domain : str
        The gettext domain name, typically the project name (e.g., "checkconnect").
    locale_dir : str
        The directory where the compiled `.mo` translation files are located.
    language : str
        The current language code in use (e.g., "en", "de").
    translation : gettext.NullTranslations
        The active gettext translation object.
    _ : Callable
        A shorthand alias for gettext's translation function.

    """

    _internal_errors: list[str]

    APP_NAME: Final[str] = __app_name__.lower()
    LOCALES_DIR_NAME: Final[str] = "locales"

    def __init__(self) -> None:
        """
        Initialize TranslationManager attributes.

        Does NOT load translations yet.
        Call .configure() to set up translations.
        """
        print("[DEBUG] TranslationManager instance created (lightweight init)")

        self.translation_domain: str = self.APP_NAME
        self.locale_dir: Path | None = None
        self.current_language: str | None = None
        self.translation: gettext.NullTranslations = gettext.NullTranslations()
        self._: Callable[[str], str] = self.translation.gettext
        self._internal_errors: list[str] = []  # Errors specific to this instance's setup

    def configure(
        self,
        language: str | None = None,
        translation_domain: str | None = None,
        locale_dir: str | None = None,
    ) -> None:
        """
        Configure and loads translations for the TranslationManager.

        This method should be called by the Singleton manager.

        Parameters:
        - language: The language code to use for translations.
        - translation_domain: The domain for translations.
        - locale_dir: The directory containing translation files.

        Returns:
            None

        """
        """
        Configures and loads translations for the TranslationManager.
        This method should be called by the Singleton manager.
        """
        if self.current_language is not None and self.current_language == language:
            # Already configured with the same language, possibly skip or log
            print(f"[DEBUG] TranslationManager already configured for language: {language}")
            return

        self._internal_errors.clear()  # Clear errors for fresh configuration attempt

        print(f"[DEBUG] Configuring TranslationManager with language: {language}")
        print(f"[DEBUG] Translation domain (initial): {translation_domain}")
        print(f"[DEBUG] Locale directory (initial): {locale_dir}")

        self.translation_domain = translation_domain or self.APP_NAME
        self.locale_dir = Path(locale_dir) if locale_dir else self._default_locale_dir()

        # Resolve language if not provided
        resolved_language = language
        if not resolved_language:
            # IMPORTANT: Access SettingsManagerSingleton *here*, in the configure phase.
            try:
                settings_lang = SettingsManagerSingleton.get_instance().get_setting("general", "default_language")
                if settings_lang:
                    resolved_language = settings_lang
                else:
                    system_lang = self._get_system_language()
                    resolved_language = system_lang or "en"
            except Exception as e:
                self._internal_errors.append(f"Could not retrieve default language from settings/system: {e}")
                resolved_language = "en"  # Fallback
            print(f"[DEBUG] resolved language: {resolved_language}")

        print(f"[DEBUG] Final locale directory: {self.locale_dir}")
        print(f"[DEBUG] Final translation domain: {self.translation_domain}")

        try:
            self.translation = gettext.translation(
                self.translation_domain,
                localedir=self.locale_dir,
                languages=[resolved_language],
                fallback=True,
            )
            self._ = self.translation.gettext
            self.current_language = resolved_language
            # It's generally better to setlocale once globally at app startup
            # if possible, or be very mindful of its thread-safety implications.
            # For now, keeping it here but be aware.
            locale.setlocale(locale.LC_ALL, resolved_language)
            print(f"[DEBUG] Locale set to: {resolved_language}")
        except Exception as e:
            msg = f"Translation for '{resolved_language}' failed to load from '{self.locale_dir}': {e}"
            logger.warning(msg)
            print(f"[DEBUG] {msg}")
            self._internal_errors.append(msg)
            self.current_language = resolved_language  # Still track what we tried to set
            self._ = gettext.gettext  # Fallback to default gettext (returns original string)

    def _default_locale_dir(self) -> Path:
        """
        Determine the default directory for translation files.

        Returns
        -------
        Path
            Path to the default "locales" directory inside the project.

        """
        locales_dir = Path(__file__).parent.parent / self.LOCALES_DIR_NAME
        if locales_dir.exists():
            return locales_dir

        return Path(self._package_locale_dir())

    def _package_locale_dir(self) -> str:
        """Fallback: Lokale Übersetzungen aus dem PyPI-Package verwenden."""
        try:
            return str(
                importlib.resources.files(self.APP_NAME) / self.LOCALES_DIR_NAME,
            )
        except Exception as e:
            self._internal_errors.append(f"Failed to resolve package locale directory for '{self.APP_NAME}': {e}")
            # Fallback for when importlib.resources.files might fail
            return str(Path(__file__).parent.parent / self.LOCALES_DIR_NAME)

    def _set_language(self) -> None:
        """
        Set the language for translations.

        Tries (1) explicit language, (2) config setting, (3) system locale, (4) fallback to 'en'.

        """
        lang = self.current_language

        if not lang:
            settings_lang = SettingsManagerSingleton.get_instance().get_setting("general", "default_language")
            if settings_lang:
                lang = settings_lang
            else:
                system_lang = self._get_system_language()
                lang = system_lang or "en"
                print(f"[DEBUG] systemlanguage   : {system_lang}")

        print(f"[DEBUG] resolved language: {lang}")
        print(f"[DEBUG] translation domain: {self.translation_domain}")

        try:
            self.translation = gettext.translation(
                self.translation_domain,
                localedir=self.locale_dir,
                languages=[lang],
                fallback=True,
            )
            self._ = self.translation.gettext
            self.current_language = lang
            locale.setlocale(locale.LC_ALL, lang)
            print(f"[DEBUG] locale set to: {lang}")
        except Exception as e:
            logger.warning("Translation for '%s' failed: %s", lang, e)
            print("[DEBUG] locale set failed", e)
            self.current_language = lang
            self._ = gettext.gettext

    def _get_system_language(self) -> str:
        """
        Retrieve the system's default language setting.

        Returns
        -------
        str
            ISO 639-1 language code (e.g., "en", "de"). Defaults to "en" if
            locale detection fails.
        """
        print("DEBUG: _get_system_language()")
        # Try to get the language from environment variables first,
        # which is often what getdefaultlocale() would have done.
        # Common environment variables: LANGUAGE, LC_ALL, LC_MESSAGES, LANG
        for env_var in ["LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"]:
            lang_env = os.getenv(env_var)
            if lang_env:
                # Environment variables can contain multiple languages (e.g., "en_GB:en")
                # or locale strings (e.g., "en_US.UTF-8").
                # We want the first two-letter code.
                lang_code = lang_env.split(":")[0].split("_")[0].split(".")[0]
                if lang_code:
                    print(f"DEBUG: Found language code from {env_var}: {lang_code}")
                    return lang_code.lower()  # Ensure consistent lowercase

        # If environment variables don't yield a result, try locale.getlocale()
        # after setting a neutral locale, then restoring it.
        # This is a bit more complex because setlocale affects the current process.
        # However, for simply *reading* the system default, it's often the most reliable.
        # Note: This might still implicitly rely on underlying system calls that
        # getdefaultlocale() also used.
        try:
            # Save current locale to restore it later
            original_locale = locale.getlocale(locale.LC_ALL)

            # Temporarily set a neutral locale to ensure we're getting the
            # system default, not an already modified one in the process.
            # On some systems, passing an empty string to LC_ALL gets the user's default.
            locale.setlocale(locale.LC_ALL, "")

            # Now, get the locale for LC_CTYPE which typically contains language info
            lang, _ = locale.getlocale(locale.LC_CTYPE)
            if lang:
                # Extract the base language code (e.g., "en_US" -> "en")
                print("DEBUG: Retrieved locale", lang)
                return lang.split("_")[0].lower()
        except locale.Error as e:
            # Handle cases where locale operations might fail
            print("DEBUG: Failed to retrieve locale", e)
        finally:
            # Always restore the original locale
            if "original_locale" in locals() and original_locale[0] is not None:
                try:
                    locale.setlocale(locale.LC_ALL, original_locale)
                except locale.Error:
                    # If restoring fails, it's a minor issue for this specific function,
                    # but might indicate a deeper problem with locale setup.
                    pass

        return "en"  # Fallback to English

    def translate(self, text: str) -> str:
        """Übersetzt einen Text."""
        return self.translation.gettext(text)

    def translate_plural(self, singular: str, plural: str, count: int) -> str:
        """Übersetzt mit Singular- und Pluralformen."""
        if not self.translation:
            raise AttributeError("Translation object not initialized.")
        return self.translation.ngettext(singular, plural, count) % count

    def translate_context(self, context: str, text: str) -> str:
        """
        Translate the context (like pgettext).

        Convention: Context and text are separeatd with a `|` in the .po-files.
        """
        return self.translation.gettext(f"{context}|{text}")

    def gettext(self, message: str) -> str:
        """
        Translate a given string.

        Parameters
        ----------
        text : str
            The message string to be translated.

        Returns
        -------
        str
            The translated string based on current language settings.

        """
        return self._(message)

    def set_language(self, language: str) -> None:
        """
        Change the active language and reload translations.

        Parameters
        ----------
        language : str
            New language code to activate (e.g., "fr", "de").

        """
        self.current_language = language
        self._set_language()

    def get_current_language(self) -> str:
        """Gibt die aktuelle Sprache zurück."""
        return self.current_language

    def get_instance_errors(self) -> list[str]:
        """Exposes internal errors encountered during configuration."""
        return list(self._internal_errors)


class TranslationManagerSingleton:
    """
    Singleton class for TranslationManager.

    Ensures a single instance manages application translations
    and handles its controlled initialization.
    """

    _instance: TranslationManager | None = None
    _initialization_errors: ClassVar[list[str]] = []
    _is_configured: ClassVar[bool] = False  # Track if the instance has been configured

    @classmethod
    def get_instance(cls) -> TranslationManager:
        """
        Return the single instance of TranslationManager.

        Raises RuntimeError if not yet initialized.
        """
        if cls._instance is None:
            try:
                cls._instance = TranslationManager()
            except Exception as e:
                cls._initialization_errors.append(f"Error creating TranslationManager instance: {e}")
                cls._instance = None
                raise
        return cls._instance

    @classmethod
    def configure_instance(
        cls,
        language: str | None = None,
        translation_domain: str | None = None,
        locale_dir: str | None = None,
    ) -> None:
        """
        Configure the TranslationManager instance.

        This should be called
        once during application startup after the instance is obtained.
        """
        if cls._is_configured:
            # Optional: Decide if you want to allow re-configuration or log a warning
            print("[DEBUG] TranslationManagerSingleton already configured. Skipping re-configuration.")
            # For now, let's allow it to potentially re-run configure on the instance
            # but clear singleton errors for this attempt.
            # If you want strict single-time configuration for the app lifecycle:
            # cls._initialization_errors.append("TranslationManagerSingleton already configured. Cannot re-configure.")
            # return

        instance = cls.get_instance()  # Ensure instance exists

        cls._initialization_errors.clear()  # Clear errors for a fresh configuration attempt
        try:
            instance.configure(
                language=language,
                translation_domain=translation_domain,
                locale_dir=locale_dir,
            )
            # Add errors reported by the instance itself
            cls._initialization_errors.extend(instance.get_instance_errors())
            cls._is_configured = True
        except Exception as e:
            msg = f"Critical error during TranslationManager configuration: {e}"
            cls._initialization_errors.append(msg)
            print(f"[DEBUG] {msg}")
            raise  # Re-raise if configuration failed critically

    @classmethod
    def get_initialization_errors(cls) -> list[str]:
        """Exposes initialization errors for testing/debugging."""
        errors = list(cls._initialization_errors)
        if cls._instance:
            errors.extend(cls._instance.get_instance_errors())  # Now calling public method
        return list(set(errors))  # Return unique errors

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton instance and its configuration state.

        Primarily for testing.
        """
        cls._instance = None
        cls._initialization_errors.clear()
        cls._is_configured = False
