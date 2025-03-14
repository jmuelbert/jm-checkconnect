# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#
"""
Translation Management Script for CheckConnect.

This script automates the process of updating and compiling translations
for both Qt (using PySide6) and Python (using Babel).
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.theme import Theme

# Rich console setup
custom_theme = Theme(
    {
        "info": Style(color="cyan", bold=True),
        "success": Style(color="green", bold=True),
        "warning": Style(color="yellow", bold=True),
        "error": Style(color="red", bold=True),
        "module": Style(color="magenta", bold=True),
    },
)
console = Console(theme=custom_theme)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
SRC_DIR = PROJECT_ROOT / "src" / "checkconnect"
GUI_DIR = SRC_DIR / "gui"
CLI_DIR = SRC_DIR / "cli"
CORE_DIR = SRC_DIR / "core"

# Translation directories
GUI_LOCALES_DIR = GUI_DIR / "locales"
CLI_LOCALES_DIR = CLI_DIR / "locales"
CORE_LOCALES_DIR = CORE_DIR / "locales"


@dataclass
class TranslationConfig:
    """
    Configuration for the Translation Update Script.

    Attributes
    ----------
        languages (list[str]): List of language codes to update.
        config_path (Path): Path to the configuration file.

    """

    languages: Optional[list[str]] = None
    config_path: Path = PROJECT_ROOT / "scripts" / "translation_config.yml"

    @classmethod
    def from_yaml(cls, path: Path) -> "TranslationConfig":
        """
        Load configuration from a YAML file.

        Args:
        ----
            path (Path): Path to the YAML configuration file.

        Returns:
        -------
            TranslationConfig: Configuration loaded from the file.

        """
        try:
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            console.print(
                "[warning]Config file not found: {path}, "
                "using default settings.[/warning]",
            )
            return cls()
        except yaml.YAMLError as e:
            console.print(f"[error]Error parsing config file: {path} - {e}[/error]")
            sys.exit(1)

        return cls(languages=config.get("languages", []))


def ensure_dir_exists(directory: Path) -> None:
    """Ensure that the directory exists."""
    directory.mkdir(parents=True, exist_ok=True)


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[bool, str]:
    """
    Run a shell command and return its success status and output.

    Args:
    ----
        cmd (list[str]): Command to run as a list of strings.
        cwd (Optional[Path]): Working directory for the command.

    Returns:
    -------
        Tuple[bool, str]: Tuple containing success status (bool) and output
            (str).

    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd if cwd else PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"


def update_qt_translations() -> None:
    """Update and compile Qt translations using PySide6 tools."""
    console.print(Panel("[info]Updating Qt Translations[/info]", border_style="info"))

    # Ensure locale directories exist
    ensure_dir_exists(GUI_LOCALES_DIR)

    # Find all Qt UI files and Python files in GUI directory
    gui_python_files = list(GUI_DIR.glob("**/*.py"))

    # For each language
    for lang in config.languages:
        ts_file = GUI_LOCALES_DIR / f"checkconnect_{lang}.ts"
        qm_file = GUI_LOCALES_DIR / f"checkconnect_{lang}.qm"

        # Create .ts file if it doesn't exist
        if not ts_file.exists():
            console.print(
                f"[warning]Creating new translation file: {ts_file}[/warning]",
            )
            # Create an empty .ts file
            with open(ts_file, "w") as f:
                f.write(
                    f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="{lang}">
</TS>
""",
                )

        # Update .ts file
        console.print(f"[info]Updating {ts_file}...[/info]")
        success, output = run_command(
            [
                "pyside6-lupdate",
                *map(str, gui_python_files),  # Convert Path objects to strings
                "-ts",
                str(ts_file),
            ],
        )

        if not success:
            console.print(f"[error]Error updating {ts_file}: {output}[/error]")
            continue

        # Compile .ts to .qm
        console.print(f"[info]Compiling {qm_file}...[/info]")
        success, output = run_command(
            [
                "pyside6-lrelease",
                str(ts_file),
                "-qm",
                str(qm_file),
            ],
        )

        if not success:
            console.print(f"[error]Error compiling {ts_file}: {output}[/error]")
            continue

        console.print(
            f"[success]Successfully updated and compiled {lang} Qt "
            "translation[/success]",
        )


def update_babel_translations() -> None:
    """Update and compile Python translations using Babel."""
    console.print(
        Panel("[info]Updating Python Translations[/info]", border_style="info"),
    )

    # Ensure locale directories exist
    for locale_dir in [CLI_LOCALES_DIR, CORE_LOCALES_DIR]:
        ensure_dir_exists(locale_dir)

    # Extract messages from Python files
    for module_dir, locale_dir in [
        (CLI_DIR, CLI_LOCALES_DIR),
        (CORE_DIR, CORE_LOCALES_DIR),
    ]:
        module_name = module_dir.name
        pot_file = locale_dir / f"{module_name}.pot"

        console.print(
            f"[module]Extracting messages from {module_name} module...[/module]",
        )

        # Find all Python files
        python_files = list(module_dir.glob("**/*.py"))
        if not python_files:
            console.print(f"[warning]No Python files found in {module_dir}[/warning]")
            continue

        # Extract messages to POT file
        success, output = run_command(
            [
                "pybabel",
                "extract",
                "-o",
                str(pot_file),
                *map(str, python_files),  # Convert Path objects to strings
            ],
        )

        if not success:
            console.print(f"[error]Error extracting messages: {output}[/error]")
            continue

        console.print(f"[success]Created/updated {pot_file}[/success]")

        # Update or initialize PO files for each language
        for lang in config.languages:
            lang_dir = locale_dir / lang / "LC_MESSAGES"
            ensure_dir_exists(lang_dir)
            po_file = lang_dir / f"{module_name}.po"

            if po_file.exists():
                # Update existing PO file
                console.print(f"[info]Updating {po_file}...[/info]")
                success, output = run_command(
                    [
                        "pybabel",
                        "update",
                        "-i",
                        str(pot_file),
                        "-d",
                        str(locale_dir),
                        "-l",
                        lang,
                    ],
                )
            else:
                # Initialize new PO file
                console.print(f"[warning]Creating new {po_file}...[/warning]")
                success, output = run_command(
                    [
                        "pybabel",
                        "init",
                        "-i",
                        str(pot_file),
                        "-d",
                        str(locale_dir),
                        "-l",
                        lang,
                    ],
                )

            if not success:
                console.print(
                    f"[error]Error updating/initializing {po_file}: {output}[/error]",
                )
                continue

            # Compile PO file to MO file
            console.print(f"[info]Compiling {po_file}...[/info]")
            success, output = run_command(
                [
                    "pybabel",
                    "compile",
                    "-d",
                    str(locale_dir),
                    "-l",
                    lang,
                    "--statistics",
                ],
            )

            if not success:
                console.print(f"[error]Error compiling {po_file}: {output}[/error]")
                continue

            console.print(
                f"[success]Successfully updated and compiled {lang} translation "
                f"for {module_name}[/success]",
            )


def create_default_config(config_path: Path) -> TranslationConfig:
    """Create a default translation_config.yml config file."""
    config = TranslationConfig(
        languages=["de", "fr", "es", "it"],
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {
                    "languages": config.languages,
                },
                f,
                indent=2,  # Add indentation for readability
            )
        console.print(
            f"[success]Created default configuration at {config_path}[/success]",
        )
    except Exception as e:
        console.print(f"[error]Error creating config file: {e}[/error]")
        sys.exit(1)
    return config


def main() -> int:
    """Main function to parse arguments and run translation updates."""
    parser = argparse.ArgumentParser(description="Manage CheckConnect translations")
    parser.add_argument(
        "--qt-only",
        action="store_true",
        help="Only update Qt translations",
    )
    parser.add_argument(
        "--babel-only",
        action="store_true",
        help="Only update Babel translations",
    )
    parser.add_argument(
        "--languages",
        type=str,
        help="Comma-separated list of language codes (default: all)",
    )

    args = parser.parse_args()

    # Load configuration
    global config  # Declare config as global to modify it
    config = TranslationConfig()
    if not config.config_path.exists():
        config = create_default_config(config.config_path)
    else:
        config = TranslationConfig.from_yaml(config.config_path)

    if args.languages:
        config.languages = args.languages.split(",")
        console.print(
            f"[info]Using languages from command line: "
            f"{', '.join(config.languages)}[/info]",
        )
    elif config.languages:
        console.print(
            f"[info]Using languages from config file: "
            f"{', '.join(config.languages)}[/info]",
        )
    else:
        console.print("[info]No languages specified, using all available.[/info]")

    # Check dependencies
    try:
        run_command(["pyside6-lupdate", "--version"])
    except FileNotFoundError:
        console.print(
            "[error]Error: pyside6-lupdate not found. Install PySide6 with: "
            "pip install PySide6[/error]",
        )
        return 1

    try:
        run_command(["pybabel", "--version"])
    except FileNotFoundError:
        console.print(
            "[error]Error: pybabel not found. Install Babel with: pip install "
            "Babel[/error]",
        )
        return 1

    # Run requested operations
    if args.babel_only:
        update_babel_translations()
    elif args.qt_only:
        update_qt_translations()
    else:
        update_qt_translations()
        update_babel_translations()

    console.print(
        Panel("[success]Translation update complete![/success]", border_style="success"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
