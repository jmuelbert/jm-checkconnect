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

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.theme import Theme

# Rich console setup
custom_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "verbose": "magenta",
    },
)
console = Console(theme=custom_theme)

NUMBER_OF_PARTS_TRANSLATION_NUMBER = 3 #Number of parts for a file path name.lang.md


@dataclass
class TranslationStats:
    """Data class to hold translation statistics."""

    english_docs: set[str]
    translated_docs: dict[str, set[str]]


class TranslationCoverageCalculator:
    """
    Calculates translation coverage for a documentation directory.
    """

    def __init__(self, docs_dir: Path, verbose: bool = False) -> None:
        """
        Initialize the calculator with the documentation directory.

        Args:
        ----
            docs_dir: The path to the documentation directory.
            verbose: Enable verbose output.

        """
        self.docs_dir = docs_dir
        self.verbose = verbose

    def collect_translation_stats(self) -> TranslationStats:
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
                if file.endswith(".md"):
                    filepath = Path(root) / file
                    if self.verbose:
                        console.print(f"[verbose]Processing: {filepath}[/verbose]")

                    parts = file.split(".")
                    if len(parts) == 2:  # name.md (English)
                        english_docs.add(file)
                        if self.verbose:
                            console.print(
                                f"[verbose]  Detected English doc: {file}[/verbose]",
                            )
                    elif len(parts) == NUMBER_OF_PARTS_TRANSLATION_NUMBER:  # name.lang.md (Translation)
                        try:
                            lang = parts[-2]  # Extract language code
                            base_name = ".".join(parts[:-2] + [parts[-1]])  # name.md
                            if lang not in translated_docs:
                                translated_docs[lang] = set()
                            translated_docs[lang].add(base_name)
                            if self.verbose:
                                console.print(
                                    f"[verbose]  Detected translated doc "
                                    f"({lang}): {file} (Base: {base_name})[/verbose]",
                                )
                        except Exception as e:  # Refactor blind exception
                            console.print(
                                f"[warning]Could not determine language for "
                                f"{file}: {e}[/warning]",
                            )

        if self.verbose:
            console.print(f"[verbose]English docs: {english_docs}[/verbose]")
            console.print(f"[verbose]Translated docs: {translated_docs}[/verbose]")

        return TranslationStats(english_docs=english_docs,
                                translated_docs=translated_docs)

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
                    f"[verbose]  Language {lang}: {len(intersection)} "
                    "translated[/verbose]",
                )
                console.print(f"[verbose]  Intersection doc: {intersection} ")

        coverage = (
            (translated_count / (len(translated_docs) * total_docs)) * 100
            if len(translated_docs) > 0 and total_docs > 0
            else 0
        )

        return coverage


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate translation coverage for docs.",
    )
    parser.add_argument(
        "docs_dir",
        type=Path,
        help="Path to the documentation directory.",
        nargs="?",  # Make the argument optional
        default=Path("docs"),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging.",
    )
    args = parser.parse_args()

    calculator = TranslationCoverageCalculator(args.docs_dir, args.verbose)
    coverage = calculator.calculate_coverage()
    console.print(f"translation_coverage={coverage:.2f}%")
