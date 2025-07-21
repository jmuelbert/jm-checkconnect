# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w
from rich.console import Console
from rich.style import Style
from rich.theme import Theme

custom_theme: Theme = Theme(
    {
        "info": Style(color="cyan", bold=True),
        "success": Style(color="green", bold=True),
        "warning": Style(color="yellow", bold=True),
        "error": Style(color="red", bold=True),
        "file": Style(color="magenta", bold=False),
    },
)

console = Console(theme=custom_theme)


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
        config_path (Path): Path to the TOML configuration file.

    """

    min_length: int = 100
    required_sections: set[str] = field(default_factory=set)
    supported_languages: set[str] = field(default_factory=set)
    code_example_required: bool = True
    image_required: bool = False
    config_path: Path = Path("scripts") / "doc_quality.toml"  # Change to .toml

    @classmethod
    def from_toml(cls, path: Path) -> DocConfig:
        """
        Load configuration from a TOML file.

        Args:
        ----
            path (Path): Path to the TOML configuration file.

        Returns:
        -------
            DocConfig: A DocConfig instance with values from the TOML file.

        """
        try:
            with path.open("rb") as f:  # Open the file in binary mode
                config_data = tomllib.load(f)  # Load the TOML file
        except FileNotFoundError:
            console.print(f"[error]Config file not found: {path}[/error]")
            sys.exit(1)
        except tomllib.TOMLDecodeError as e:
            console.print(f"[error]Error parsing config file: {path} - {e}[/error]")
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

    @classmethod
    def create_default_config(cls, config_path: Path) -> DocConfig:
        """
        Create a default doc_quality.toml config file.

        Args:
        ----
            config_path (Path): Path to the configuration file.

        Returns:
        -------
            DocConfig: A DocConfig instance representing the default
                configuration.

        """
        config = cls(
            min_length=100,
            required_sections={"Installation", "Usage", "Configuration"},
            supported_languages={"en", "de", "it", "es"},
            code_example_required=True,
            image_required=True,
        )

        # Ensure the parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with config_path.open("w", encoding="utf-8") as f:
                tomli_w.dump(
                    {
                        "min_length": config.min_length,
                        "required_sections": list(config.required_sections),
                        "supported_languages": list(config.supported_languages),
                        "code_example_required": config.code_example_required,
                        "image_required": config.image_required,
                    },
                    f,
                )
            console.print(f"[success]Created default configuration at {config_path}[/success]")
        except (OSError, PermissionError) as e:
            console.print(f"[error]Error creating config file: {e}[/error]")
            sys.exit(1)

        return config
