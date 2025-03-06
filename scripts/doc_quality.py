"""Enhanced documentation quality checker with i18n suffix support."""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.theme import Theme

# Rich console setup
custom_theme = Theme({
    "info": Style(color="cyan", bold=True),
    "success": Style(color="green", bold=True),
    "warning": Style(color="yellow", bold=True),
    "error": Style(color="red", bold=True),
    "file": Style(color="magenta", bold=False),
})
console = Console(theme=custom_theme)


def get_project_root() -> Path:
    """Get the project root directory."""
    # This script is at ROOT/scripts/doc_quality.py
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
DOCS_DIR = PROJECT_ROOT / "docs"


@dataclass
class DocConfig:
    """Documentation configuration."""

    min_length: int = 100
    required_sections: set[str] = None
    supported_languages: set[str] = None
    code_example_required: bool = True
    image_required: bool = False
    config_path: Path = PROJECT_ROOT / "docs" / "config" / "doc_quality.yml"

    @classmethod
    def from_yaml(cls, path: Path) -> "DocConfig":
        """Load configuration from YAML file."""
        try:
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[error]Config file not found: {path}[/error]")
            sys.exit(1)  # Exit if the config file is missing
        except yaml.YAMLError as e:
            console.print(f"[error]Error parsing config file: {path} - {e}[/error]")
            sys.exit(1)  # Exit if there's a YAML parsing error

        return cls(
            min_length=config.get("min_length", 100),
            required_sections=set(config.get("required_sections", [])),
            supported_languages=set(config.get("supported_languages", [])),
            code_example_required=config.get("code_example_required", True),
            image_required=config.get("image_required", False),
        )


class DocChecker:
    """Documentation quality checker."""

    def __init__(self, config: DocConfig):
        self.config = config
        self.console = console  # Use the global console object
        self.issues: dict[str, list[str]] = {}

    def check_markdown(self, file_path: Path) -> None:
        """Check a markdown file for quality issues."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            self.console.print(f"[error]File not found: {file_path}[/error]")
            self.issues[str(file_path)] = ["File not found"]
            return
        except Exception as e:
            self.console.print(f"[error]Error reading file: {file_path} - {e}[/error]")
            self.issues[str(file_path)] = [f"Error reading file: {e}"]
            return


        file_issues = []

        # Basic checks
        if len(content) < self.config.min_length:
            file_issues.append(f"[warning]Content too short ({len(content)} chars)[/warning]")

        if not re.search(r"^#\s.+", content, re.MULTILINE):
            file_issues.append("[error]Missing main header[/error]")

        # Code examples
        if self.config.code_example_required and file_path.stem not in [
            "changelog",
            "license",
        ]:
            if not re.search(r"```.*\n", content):
                file_issues.append("[warning]No code examples found[/warning]")

        # Section checks
        if self.config.required_sections:
            sections = set(re.findall(r"^##\s+(.+)$", content, re.MULTILINE))
            missing = self.config.required_sections - sections
            if missing:
                file_issues.append(f"[error]Missing required sections: {', '.join(missing)}[/error]")

        # Image checks
        if self.config.image_required:
            if not re.search(r"!\[.*\]\(.*\)", content):
                file_issues.append("[warning]No images found[/warning]")

        # Links check
        links = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content)
        for text, url in links:
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
        """Extract language code from file path (suffix method)."""
        file_name = file_path.name
        parts = file_name.split(".")  # Split by dots
        if len(parts) > 2:  # Check if there's a language suffix (e.g., index.en.md)
            lang = parts[-2]  # Language code is the second to last part
            if lang in self.config.supported_languages:
                return lang
        return None


    def check_translations(self, docs_dir: Path) -> None:
        """Check if all documents are translated (suffix method)."""
        base_docs: set[str] = set()
        translated_docs: dict[str, set[str]] = {
            lang: set() for lang in self.config.supported_languages
        }

        # Collect all documents
        for file in docs_dir.rglob("*.md"):
            lang = self._get_language_code(file)
            file_stem = file.name
            if lang:
                #It is a translation
                file_stem = ".".join(file.name.split(".")[:-2]) + ".md"
                translated_docs[lang].add(file_stem)
            else:
                #It is a default language
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
            table = Table(title="[error]Documentation Quality Report[/error]", show_lines=True)
            table.add_column("[file]File[/file]", style="file")
            table.add_column("[error]Issues[/error]", style="error", overflow="fold")

            for file, file_issues in self.issues.items():
                table.add_row(file, "\n".join(file_issues))

            self.console.print(table)
        else:
            self.console.print(Panel("[success]Documentation quality check passed![/success]", border_style="success"))


def create_default_config(config_path: Path) -> DocConfig:
    """Creates a default doc_quality.yml config file."""
    config = DocConfig(
        min_length=100,
        required_sections={"Installation", "Usage", "Configuration"},
        supported_languages={"en", "de", "it", "es"},
        code_example_required=True,
        image_required=True,
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
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
            )
        console.print(f"[success]Created default configuration at {config_path}[/success]")
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
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
