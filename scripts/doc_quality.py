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

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Self  # Keep Self

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.theme import Theme

# Constants
LINE_LENGTH_LIMIT = 79  # Standard Python line length limit
NUMBER_OF_PARTS_FILE_PATH_NUMBER: int = 2


# Rich console setup
custom_theme = Theme(
    {
        "info": Style(color="cyan", bold=True),
        "success": Style(color="green", bold=True),
        "warning": Style(color="yellow", bold=True),
        "error": Style(color="red", bold=True),
        "file": Style(color="magenta", bold=False),
    },
)
custom_theme = Theme(
    {
        "info": Style(color="cyan", bold=True),
        "success": Style(color="green", bold=True),
        "warning": Style(color="yellow", bold=True),
        "error": Style(color="red", bold=True),
        "file": Style(color="magenta", bold=False),
    },
)
console = Console(theme=custom_theme)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
DOCS_DIR = PROJECT_ROOT / "docs"


@dataclass
class DocConfig:
    """
    Configuration for Documentation Quality Checks.

    Attributes
    ----------
        min_length (int): Minimum content length in characters.
        required_sections (set[str]): Set of required section headers.
        supported_languages (set[str]): Set of supported language codes.
        code_example_required (bool): Whether code examples are required.
        image_required (bool): Whether images are required.
        config_path (Path): Path to the YAML configuration file.

    """

    min_length: int = 100
    required_sections: set[str] = field(default_factory=set)
    supported_languages: set[str] = field(default_factory=set)
    code_example_required: bool = True
    image_required: bool = False
    config_path: Path = PROJECT_ROOT / "scripts" / "doc_quality.yml"

    @classmethod
    def from_yaml(cls, path: Path) -> Self:
        """
        Load configuration from a YAML file.

        Args:
        ----
            path (Path): Path to the YAML configuration file.

        Returns:
        -------
            DocConfig: A DocConfig instance with values from the YAML file.

        """
        try:
            with path.open(encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[error]Config file not found: {path}[/error]")
            sys.exit(1)
        except yaml.YAMLError as e:
            console.print(
                f"[error]Error parsing config file: {path} - {e}[/error]",
            )
            sys.exit(1)

        # Extract values from the loaded data, providing defaults
        min_length = config_data.get("min_length", 100)
        required_sections = set(config_data.get("required_sections", []))
        supported_languages = set(config_data.get("supported_languages", []))
        code_example_required = config_data.get("code_example_required", True)
        image_required = config_data.get("image_required", False)

        return cls(
            min_length=min_length,
            required_sections=required_sections,
            supported_languages=supported_languages,
            code_example_required=code_example_required,
            image_required=image_required,
        )


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

    def _read_file(self, file_path: Path) -> Optional[str]:
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
        except OSError as e:
            self.console.print(
                f"[error]Error reading file: {file_path} - {e}[/error]",
            )
            self.issues[str(file_path)] = [f"Error reading file: {e}"]
            return

        file_issues = []

        # Basic checks
        if len(content) < self.config.min_length:
            file_issues.append(
                f"[warning]Content too short ({len(content)} chars)[/warning]",
            )
            file_issues.append(
                f"[warning]Content too short ({len(content)} chars)[/warning]",
            )

        if not re.search(r"^#\s.+", content, re.MULTILINE):
            file_issues.append("[error]Missing main header[/error]")

        # Code examples
        if (
            self.config.code_example_required
            and file_path.stem not in ["changelog", "license"]
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
                file_issues.append(
                    f"[error]Missing required sections: {', '.join(missing)}[/error]",
                )

        # Image checks
        if self.config.image_required:
            if not re.search(r"!\[.*\]\(.*\)", content):
                file_issues.append("[warning]No images found[/warning]")

        # Links check
        links: list[tuple[str, str]] = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content)
        for _, url in links:  # Remove Unused variable
            if not url.startswith(("http", "#", "/", "..")):
                file_issues.append(f"[error]Invalid link: {url}[/error]")

        # Language-specific checks
        lang_code = self._get_language_code(file_path)
        if lang_code and lang_code not in self.config.supported_languages:
            file_issues.append(f"[error]Unsupported language: {lang_code}[/error]")

        if file_issues:
            self.issues[str(file_path)] = file_issues
            self.console.print(f"[file]{file_path}[/file]:")
            for issue in file_issues:
                self.console.print(f"  - {issue}")

    def _get_language_code(self, file_path: Path) -> Optional[str]:
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
            if (
                len(parts) > NUMBER_OF_PARTS_FILE_PATH_NUMBER
                and lang in self.config.supported_languages
            ):
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
        translated_docs: dict[str, set[str]] = {
            lang: set() for lang in self.config.supported_languages
        }

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


def create_default_config(config_path: Path) -> DocConfig:
    """
    Create a default doc_quality.yml config file.

    Args:
    ----
        config_path (Path): Path to the configuration file.

    Returns:
    -------
        DocConfig: A DocConfig instance representing the default
            configuration.

    """
    config = DocConfig(
        min_length=100,
        required_sections={"Installation", "Usage", "Configuration"},
        supported_languages={"en", "de", "it", "es"},
        code_example_required=True,
        image_required=True,
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with config_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "min_length": config.min_length,
                    "required_sections": list(config.required_sections),
                    "supported_languages": list(config.supported_languages),
                    "code_example_required": config.code_example_required,
                    "image_required": config.image_required,
                },
                f,
                indent=2,  # Add indentation for readability
                width=LINE_LENGTH_LIMIT,  # Respect line length limit
            )
        console.print(
            f"[success]Created default configuration at {config_path}[/success]",
        )
    except Exception as e:
        console.print(f"[error]Error creating config file: {e}[/error]")
        sys.exit(1)
    return config


def main() -> int:
    """Run documentation quality checks."""
    config = DocConfig()  # Create a DocConfig object to access config_path

    # Load configuration or create default
    if not config.config_path.exists():
        config = create_default_config(config.config_path)
    else:
        config = DocConfig.from_yaml(config.config_path)

    checker = DocChecker(config)

    # Check all markdown files
    for md_file in DOCS_DIR.rglob("*.md"):
        checker.check_markdown(md_file)

    # Check translations
    checker.check_translations(DOCS_DIR)

    # Generate report
    checker.generate_report()

    if checker.issues:
        console.print("[error]Documentation quality check failed.[/error]")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
