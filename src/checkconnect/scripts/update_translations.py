#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#
"""
Translation Management Script for CheckConnect

This script automates the process of updating and compiling translations
for both Qt (using PySide6) and Python (using Babel).
"""

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def get_project_root():
    """Get the project root directory."""
    # This script is at ROOT/src/checkconnect/scripts/update_translations.py
    return Path(__file__).resolve().parent.parent.parent.parent

PROJECT_ROOT = get_project_root()
SRC_DIR = PROJECT_ROOT / "src" / "checkconnect"
SRC_DIR = PROJECT_ROOT / "src" / "checkconnect"
GUI_DIR = SRC_DIR / "gui"
CLI_DIR = SRC_DIR / "cli"
CORE_DIR = SRC_DIR / "core"

# Translation directories
GUI_LOCALES_DIR = GUI_DIR / "locales"
CLI_LOCALES_DIR = CLI_DIR / "locales"
CORE_LOCALES_DIR = CORE_DIR / "locales"

# Supported languages (ISO language codes)
LANGUAGES = ["de", "fr", "es", "it"]  # Add more as needed


def ensure_dir_exists(directory: Path) -> None:
    """Ensure that the directory exists."""
    directory.mkdir(parents=True, exist_ok=True)


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[bool, str]:
    """
    Run a shell command and return its success status and output.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command

    Returns:
        Tuple of (success, output)

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
    print("=== Updating Qt Translations ===")

    # Ensure locale directories exist
    ensure_dir_exists(GUI_LOCALES_DIR)

    # Find all Qt UI files and Python files in GUI directory
    gui_python_files = list(GUI_DIR.glob("**/*.py"))

    # For each language
    for lang in LANGUAGES:
        ts_file = GUI_LOCALES_DIR / f"checkconnect_{lang}.ts"
        qm_file = GUI_LOCALES_DIR / f"checkconnect_{lang}.qm"

        # Create .ts file if it doesn't exist
        if not ts_file.exists():
            print(f"Creating new translation file: {ts_file}")
            # Create an empty .ts file
            with open(ts_file, 'w') as f:
                f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="{lang}">
</TS>
""")

        # Update .ts file
        print(f"Updating {ts_file}...")
        source_files = " ".join(str(f) for f in gui_python_files)
        success, output = run_command([
            "pyside6-lupdate",
            *gui_python_files,
            "-ts", str(ts_file),
        ])

        if not success:
            print(f"Error updating {ts_file}: {output}")
            continue

        # Compile .ts to .qm
        print(f"Compiling {qm_file}...")
        success, output = run_command([
            "pyside6-lrelease",
            str(ts_file),
            "-qm", str(qm_file),
        ])

        if not success:
            print(f"Error compiling {ts_file}: {output}")
            continue

        print(f"Successfully updated and compiled {lang} Qt translation")


def update_babel_translations() -> None:
    """Update and compile Python translations using Babel."""
    print("\n=== Updating Python Translations ===")

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

        print(f"Extracting messages from {module_name} module...")

        # Find all Python files
        python_files = list(module_dir.glob("**/*.py"))
        if not python_files:
            print(f"No Python files found in {module_dir}")
            continue

        # Extract messages to POT file
        success, output = run_command([
            "pybabel", "extract",
            "-o", str(pot_file),
            *[str(f) for f in python_files],
        ])

        if not success:
            print(f"Error extracting messages: {output}")
            continue

        print(f"Created/updated {pot_file}")

        # Update or initialize PO files for each language
        for lang in LANGUAGES:
            lang_dir = locale_dir / lang / "LC_MESSAGES"
            ensure_dir_exists(lang_dir)
            po_file = lang_dir / f"{module_name}.po"

            if po_file.exists():
                # Update existing PO file
                print(f"Updating {po_file}...")
                success, output = run_command([
                    "pybabel", "update",
                    "-i", str(pot_file),
                    "-d", str(locale_dir),
                    "-l", lang,
                ])
            else:
                # Initialize new PO file
                print(f"Creating new {po_file}...")
                success, output = run_command([
                    "pybabel", "init",
                    "-i", str(pot_file),
                    "-d", str(locale_dir),
                    "-l", lang,
                ])

            if not success:
                print(f"Error updating/initializing {po_file}: {output}")
                continue

            # Compile PO file to MO file
            print(f"Compiling {po_file}...")
            success, output = run_command([
                "pybabel", "compile",
                "-d", str(locale_dir),
                "-l", lang,
                "--statistics",
            ])

            if not success:
                print(f"Error compiling {po_file}: {output}")
                continue

            print(f"Successfully updated and compiled {lang} translation for {module_name}")


def main():
    """Main function to parse arguments and run translation updates."""
    parser = argparse.ArgumentParser(description="Manage CheckConnect translations")
    parser.add_argument("--qt-only", action="store_true", help="Only update Qt translations")
    parser.add_argument("--babel-only", action="store_true", help="Only update Babel translations")
    parser.add_argument("--languages", type=str, help="Comma-separated list of language codes (default: all)")

    args = parser.parse_args()

    if args.languages:
        global LANGUAGES
        LANGUAGES = args.languages.split(",")
        print(f"Using languages: {', '.join(LANGUAGES)}")

    # Check dependencies
    try:
        run_command(["pyside6-lupdate", "--version"])
    except FileNotFoundError:
        print("Error: pyside6-lupdate not found. Install PySide6 with: pip install PySide6")
        return 1

    try:
        run_command(["pybabel", "--version"])
    except FileNotFoundError:
        print("Error: pybabel not found. Install Babel with: pip install Babel")
        return 1

    # Run requested operations
    if args.babel_only:
        update_babel_translations()
    elif args.qt_only:
        update_qt_translations()
    else:
        update_qt_translations()
        update_babel_translations()

    print("\nTranslation update complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
