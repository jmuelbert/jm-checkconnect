import gettext
import importlib.resources
import os
from typing import Optional


class TranslationManager:
    def __init__(self, domain="checkconnect", default_lang: str = "en", locale_dir: str = None):
        """
        :param default_lang: Standard-Sprache (z. B. 'en', 'de', 'fr').
        :param locale_dir: Optional: Nutzerdefinierter Speicherort für Übersetzungen.
        """

        self.domain = domain
        self.current_lang = default_lang

        # Falls ein expliziter Pfad übergeben wurde, diesen nutzen
        if locale_dir:
            self.locale_dir = locale_dir
        else:
            self.locale_dir = self._detect_locale_directory()

        self.translation = self._load_translation(default_lang)

    def _detect_locale_directory(self) -> str:
        """Ermittelt den Speicherort der Übersetzungen abhängig vom OS."""
        system = platform.system()

        if system == "Linux":
            return (
                "/usr/share/locale"
                if os.path.exists("/usr/share/locale")
                else self._package_locale_dir()
            )
        elif system == "Darwin":  # macOS
            return (
                "/usr/local/share/locale"
                if os.path.exists("/usr/local/share/locale")
                else self._package_locale_dir()
            )
        elif system == "Windows":
            return os.getenv("APPDATA", "") + "\\checkconnect\\locale"
        else:
            return self._package_locale_dir()

    def _package_locale_dir(self) -> str:
        """Fallback: Lokale Übersetzungen aus dem PyPI-Package verwenden."""
        return str(importlib.resources.files("checkconnect") / "locales")

    def _load_translation(self, lang: str) -> gettext.GNUTranslations:
        """Lädt die passende `.mo`-Datei."""
        try:
            return gettext.translation(
                "messages",
                localedir=self.locale_dir,
                languages=[lang],
                fallback=True,
            )
        except FileNotFoundError:
            return gettext.NullTranslations()

    def set_language(self, lang: str):
        """Wechselt die Sprache."""
        self.current_lang = lang
        self.translation = self._load_translation(lang)
        self.translation.install()

    def translate(self, text: str) -> str:
        """Übersetzt einen Text."""
        return self.translation.gettext(text)

    def translate_plural(self, singular: str, plural: str, count: int) -> str:
        """Übersetzt mit Singular- und Pluralformen."""
        return self.translation.ngettext(singular, plural, count) % count

    def translate_context(self, context: str, text: str) -> str:
        """
        Übersetzt mit Kontext (pgettext-ähnlich).
        Konvention: Kontext und Text sind durch einen `|` getrennt in den .po-Dateien.
        """
        return self.translation.gettext(f"{context}|{text}")

    def get_current_language(self) -> str:
        """Gibt die aktuelle Sprache zurück."""
        return self.current_lang


# ---- Beispielverwendung ----
if __name__ == "__main__":
    translator = TranslationManager(locale_dir="locales", default_lang="en")

    print(translator.translate("Hello, World!"))  # Normaler Text
    print(translator.translate_plural("1 file", "{} files", 5))  # Pluralform
    print(translator.translate_context("banking", "Bank"))  # Kontextübersetzung
