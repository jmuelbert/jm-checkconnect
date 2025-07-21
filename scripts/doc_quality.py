# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#

"""
Documentation Quality Checker with i18n Suffix Support.

This script checks Markdown files for various quality issues, including:
- Minimum content length
- Presence of a main header
- Existence of code examples (if required)
- Presence of required sections
- Existence of images (if required)
- Validity of links
- Language-specific issues based on file suffix

It supports configuration via a YAML file and provides a formatted report
of any issues found.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, Final

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.utils.doc_config import DocConfig, custom_theme

# Constants
APP_NAME: Final[str] = "Documents Quality"
APP_VERSION: Final[str] = "0.2.0"
NUMBER_OF_PARTS_FILE_PATH_NUMBER: Final[int] = 2

# Rich console setup
console = Console(theme=custom_theme)
app = typer.Typer()


class DocChecker:
    """
    Documentation Quality Checker.

    This class performs various checks on Markdown files to ensure they meet
    certain quality standards.  It uses a DocConfig object to configure the
    checks.
    """

    def __init__(self, config: DocConfig) -> None:
        """
        Initialize the DocChecker.

        Args:
        ----
            config (DocConfig): The configuration for the checks.

        """
        self.config = config
        self.console = console  # Use the global console object
        self.issues: dict[str, list[str]] = {}

    def _read_file(self, file_path: Path) -> str | None:
        """
        Read file content with error handling.

        Args:
        ----
            file_path (Path): Path to the file.

        Returns:
        -------
            Optional[str]: The file content, or None if an error occurred.

        """
        try:
            with file_path.open(encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            self.console.print(f"[error]File not found: {file_path}[/error]")
            self.issues[str(file_path)] = ["File not found"]
            return None
        except (OSError, PermissionError) as e:
            self.console.print(
                f"[error]Error reading file: {file_path} - {e}[/error]",
            )
            self.issues[str(file_path)] = [f"Error reading file: {e}"]
            return None

    def _perform_checks(self, file_path: Path, content: str) -> list[str]:
        """
        Perform various quality checks on the Markdown content.

        Args:
        ----
            file_path (Path): Path to the Markdown file.
            content (str): The content of the Markdown file.

        Returns:
        -------
            list[str]: A list of issues found during the checks.

        """
        file_issues: list[str] = []

        # Basic checks
        if len(content) < self.config.min_length:
            file_issues.append(
                f"[warning]Content too short ({len(content)} chars)[/warning]",
            )

        if not re.search(r"^#\s.+", content, re.MULTILINE):
            file_issues.append("[error]Missing main header[/error]")

        # Code examples
        if (
            self.config.code_example_required
            and file_path.stem not in {"changelog", "license"}
            and not re.search(r"```.*\n", content)
        ):
            file_issues.append("[warning]No code examples found[/warning]")

        # Section checks
        if self.config.required_sections:
            sections: set[str] = set(
                re.findall(r"^##\s+(.+)$", content, re.MULTILINE),
            )
            missing: set[str] = self.config.required_sections - sections
            if missing:
                file_issues.append(
                    f"[error]Missing required sections: {', '.join(missing)}[/error]",
                )

        # Image checks
        if self.config.image_required and not re.search(r"!$$.*$$$.*$", content):
            file_issues.append("[warning]No images found[/warning]")

        # Links check
        links: list[tuple[str, str]] = re.findall(r"$$([^$$]+)\]$([^$]+)\)", content)
        for _, url in links:
            if not url.startswith(("http", "#", "/", "..")):
                file_issues.append(f"[error]Invalid link: {url}[/error]")

        # Language-specific checks
        lang_code = self._get_language_code(file_path)
        if lang_code and lang_code not in self.config.supported_languages:
            file_issues.append(f"[error]Unsupported language: {lang_code}[/error]")

        return file_issues

    def _get_language_code(self, file_path: Path) -> str | None:
        """
        Extract language code from file path (suffix method).

        Args:
        ----
            file_path (Path): Path to the file.

        Returns:
        -------
            Optional[str]: The language code, or None if not found.

        """
        file_name = file_path.name
        parts = file_name.split(".")  # Split by dots
        if len(parts) > NUMBER_OF_PARTS_FILE_PATH_NUMBER:  # Check if there's a language suffix
            lang = parts[-2]  # Language code is the second to last part
            # Check if there's a language suffix AND if language in supported languages
            if len(parts) > NUMBER_OF_PARTS_FILE_PATH_NUMBER and lang in self.config.supported_languages:
                return lang
        return None

    def check_translations(self, docs_dir: Path) -> None:
        """
        Check if all documents are translated (suffix method).

        Args:
        ----
            docs_dir (Path): Path to the documentation directory.

        """
        base_docs: set[str] = set()
        translated_docs: dict[str, set[str]] = {lang: set() for lang in self.config.supported_languages}

        # Collect all documents
        for file in docs_dir.rglob("*.md"):
            lang = self._get_language_code(file)
            file_stem = file.name
            if lang:
                # It is a translation
                # It is a translation
                file_stem = ".".join(file.name.split(".")[:-2]) + ".md"
                translated_docs[lang].add(file_stem)
            else:
                # It is a default language
                # It is a default language
                base_docs.add(file.name)

        # Check missing translations
        for lang, docs in translated_docs.items():
            missing = base_docs - docs
            if missing:
                self.issues[f"Missing {lang} translations"] = list(missing)
                self.console.print(f"[warning]Missing {lang} translations:[/warning]")
                for doc in missing:
                    self.console.print(f"  - {doc}")

    def check_markdown(self, file_path: Path) -> None:
        """
        Check a Markdown file for quality issues.

        Args:
        ----
            file_path (Path): Path to the Markdown file.

        """
        content = self._read_file(file_path)
        if content is None:
            return

        file_issues = self._perform_checks(file_path, content)

        if file_issues:
            self.issues[str(file_path)] = file_issues
            self.console.print(f"[file]{file_path}[/file]:")
            for issue in file_issues:
                self.console.print(f"  - {issue}")

    def generate_report(self) -> None:
        """Generate a formatted report of issues."""
        if self.issues:
            table = Table(
                title="[error]Documentation Quality Report[/error]",
                show_lines=True,
            )
            table.add_column("[file]File[/file]", style="file")
            table.add_column("[error]Issues[/error]", style="error", overflow="fold")

            for file, file_issues in self.issues.items():
                table.add_row(file, "\n".join(file_issues))

            self.console.print(table)
        else:
            self.console.print(
                Panel(
                    "[success]Documentation quality check passed![/success]",
                    border_style="success",
                ),
            )
            self.console.print(
                Panel(
                    "[success]Documentation quality check passed![/success]",
                    border_style="success",
                ),
            )


def version_callback(*, value: bool) -> None:
    if value:
        console.print(f"{APP_NAME} Version: {APP_VERSION}")
        raise typer.Exit


@app.command()
def doc_quality(
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
    _version: Annotated[bool | None, typer.Option("--version", callback=version_callback)] = None,
) -> None:
    """Run documentation quality checks."""
    config = DocConfig()  # Create a DocConfig object to access config_path

    # Load configuration or create default
    if not config.config_path.exists():
        config = config.create_default_config(config.config_path)
    else:
        config = DocConfig.from_toml(config.config_path)

    checker = DocChecker(config)

    docs_path = Path(docs_dir)
    # Check all markdown files
    for md_file in docs_path.rglob("*.md"):
        checker.check_markdown(md_file)

    # Check translations
    checker.check_translations(docs_path)

    # Generate report
    checker.generate_report()

    if checker.issues:
        console.print("[error]Documentation quality check failed.[/error]")
        typer.Exit(1)


def main() -> None:
    """Main entry point for CLI dispatch."""
    app()


if __name__ == "__main__":
    main()
