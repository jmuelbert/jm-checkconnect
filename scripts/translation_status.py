# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#

"""
Translation Coverage Calculator.

This script calculates the translation coverage of documentation files
in a specified directory.  It assumes English documents have the ".md"
suffix and translated documents have the "name.lang.md" naming scheme
(e.g., "document.de.md").  It uses Rich for console output.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final

import typer
from rich.console import Console

from scripts.utils.doc_config import DocConfig, custom_theme

APP_NAME: Final[str] = "Translation Status"
APP_VERSION: Final[str] = "0.2.0"
PARTS_COUNT: Final[int] = 3  # Number of parts for a file path name.lang.md
NUMBER_OF_PARTS_FILE_PATH_NUMBER: Final[int] = 2

console = Console(theme=custom_theme)
app = typer.Typer()


@dataclass
class TranslationStats:
    """Data class to hold translation statistics."""

    english_docs: set[str]
    translated_docs: dict[str, set[str]]


class TranslationCoverageCalculator:
    """Calculates translation coverage for a documentation directory."""

    def __init__(self, config: DocConfig, docs_dir: str, verbose: bool | None = None) -> None:
        """
        Initialize the calculator with the documentation directory.

        Args:
        ----
            config (DocConfig): The configuration for the checks.
            verbose: Enable verbose output.

        """
        self.config = config
        self.docs_dir = docs_dir
        self.console = console  # Use the global console object
        self.verbose = verbose

    def _process_english_doc(self, file: str, english_docs: set[str]) -> None:
        """Verarbeitet eine englische Dokumentdatei."""
        english_docs.add(file)
        if self.verbose:
            self.console.print(f"[verbose]  Detected English doc: {file}[/verbose]")

    def _process_translated_doc(self, file: str, translated_docs: dict[str, set[str]]) -> None:
        """Verarbeitet eine übersetzte Dokumentdatei."""
        try:
            parts = file.split(".")
            lang = parts[-2]
            base_name = ".".join([*parts[:-2], parts[-1]])  # name.md

            translated_docs.setdefault(lang, set()).add(base_name)

            if self.verbose:
                self.console.print(f"[verbose]  Detected translated doc ({lang}): {file} (Base: {base_name})[/verbose]")
        except IndexError:  # Wenn `parts[-2]` oder `parts[-1]` nicht existiert
            self.console.print(f"[warning]Could not parse language or base name for {file}. Skipping.[/warning]")
        except (OSError, PermissionError) as e:
            self.console.print(f"[warning]Could not determine language for {file}: {e}[/warning]")

    def collect_document_statuses(self) -> tuple[set[str], dict[str, set[str]]]:
        """
        Collect translation statistics from the documentation directory.

        Returns
        -------
            An object containing sets of English and
            translated documents.

        """
        english_docs: set[str] = set()
        translated_docs: dict[str, set[str]] = {}

        for root, _, files in os.walk(self.docs_dir):
            for file in files:
                filepath = Path(root) / file  # filePath immer definieren

                # Frühe Rückgabe / Continue für nicht-Markdown-Dateien
                if not file.endswith(".md"):
                    continue

                if self.verbose:
                    self.console.print(f"[verbose]Processing: {filepath}[/verbose]")

                parts = file.split(".")

                if len(parts) == NUMBER_OF_PARTS_FILE_PATH_NUMBER:
                    self._process_english_doc(file, english_docs)
                elif len(parts) == PARTS_COUNT:
                    self._process_translated_doc(file, translated_docs)
                # Optional: Handle andere Dateinamenskonventionen hier mit einem 'else'
                # oder lass sie einfach ignorieren.

        return english_docs, translated_docs

    def calculate_coverage(self) -> float:
        """
        Calculate the translation coverage percentage.

        Returns
        -------
            The translation coverage percentage.

        """
        stats = self.collect_translation_stats()
        english_docs = stats.english_docs
        translated_docs = stats.translated_docs

        total_docs = len(english_docs)
        translated_count = 0

        for lang, translated_bases in translated_docs.items():
            # Find the intersection of translated bases and existing english doc
            intersection = english_docs.intersection(translated_bases)
            translated_count += len(intersection)

            if self.verbose:
                console.print(
                    f"[verbose]  Language {lang}: {len(intersection)} translated[/verbose]",
                )
                console.print(f"[verbose]  Intersection doc: {intersection} ")

        return (
            (translated_count / (len(translated_docs) * total_docs)) * 100
            if len(translated_docs) > 0 and total_docs > 0
            else 0
        )


def version_callback(*, value: bool) -> None:
    if value:
        console.print(f"{APP_NAME} Version: {APP_VERSION}")
        raise typer.Exit


@app.command()
def translation_status(
    docs_dir: str = typer.Option(
        "docs",
        "--docs_dir",
        "-d",
        exists=True,
        file_okay=False,
        dir_okay=False,
        readable=True,
        help="Directory where reports will be saved (overrides config).",
        rich_help_panel="Configuration",
    ),
    verbose: Annotated[
        bool | None,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose logging output.",
            rich_help_panel="Logging",
        ),
    ] = None,
    _version: Annotated[bool | None, typer.Option("--version", callback=version_callback)] = None,
) -> None:
    config = DocConfig()
    if not config.config_path.exists():
        config = config.create_default_config(config.config_path)
    else:
        config = DocConfig.from_toml(config.config_path)

    calculator = TranslationCoverageCalculator(config, docs_dir, verbose)
    coverage = calculator.calculate_coverage()
    console.print(f"translation_coverage={coverage:.2f}%")


def main() -> None:
    """CLI dispatch for the entry point."""
    app()


if __name__ == "__main__":
    main()
