# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import importlib

import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List

import structlog

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

try:
    import tomli_w as tomlw  # Preferred TOML writer
except ImportError:
    import toml as tomlw  # type: ignore[no-redef]


log = structlog.get_logger(__name__)


class SettingsManager:
    CONFIG_LOCATIONS: ClassVar[list[str]] = [
        os.path.join(os.getcwd(), "config.toml"),  # Lokales Verzeichnis
        os.path.expanduser("~/.config/checkconnect/config.toml"),  # Linux/macOS
        os.path.join(os.getenv("APPDATA", ""), "CheckConnect", "config.toml"),  # Windows
        str(importlib.resources.files("checkconnect") / "config.toml"),  # Im installierten Package
    ]

    DEFAULT_CONFIG: ClassVar[dict[str, dict[str, Any]]] = {
        "logger": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "file_handler": {
            "enabled": True,
            "file_path": "checkconnect.log",
        },
        "limited_file_handler": {
            "enabled": True,
            "file_path": "limited_checkconnect.log",
            "max_bytes": 1024,
            "backup_count": 5,
        },
        "Output": {
            "directory": "reports",
        },
        "Files": {
            "ntp_servers": "ntp_servers.csv",
            "urls": "urls.csv",
        },
        "Network": {
            "timeout": 10,
        },
    }

    def __init__(self, config_file="config.toml"):
        """Lädt die TOML-Konfiguration."""
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> dict[str, dict[str, Any]]:
        for path_str in self.CONFIG_LOCATIONS:
            path = Path(path_str)
            if path.exists():
                try:
                    with path.open("rb") as f:
                        log.debug("Loading configuration", path=str(path))
                        return tomllib.load(f)
                except (tomllib.TOMLDecodeError, OSError) as e:
                    log.exception(
                        "Error reading configuration file",
                        path=str(path),
                        exc_info=e,
                    )

        log.warning("No configuration file found. Using default configuration.")
        self._save_default_config()
        return self.DEFAULT_CONFIG.copy()

    def _save_default_config(self) -> None:
        for path_str in self.CONFIG_LOCATIONS:
            path = Path(path_str)
            try:
                if not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as f:
                    tomlw.dump(self.DEFAULT_CONFIG, f)
                    log.info("Default configuration written to", path=str(path))
                return
            except (OSError, PermissionError) as e:
                log.exception(
                    "Error writing default configuration",
                    path=str(path),
                    exc_info=e,
                )

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.config.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        log.debug("Set config value", section=section, key=key, value=value)
        self._save_config()

    def _save_config(self) -> None:
        for path_str in self.CONFIG_LOCATIONS:
            path = Path(path_str)
            try:
                with path.open("wb") as f:
                    tomlw.dump(self.config, f)
                    log.info("Configuration saved to", path=str(path))
                return
            except (OSError, PermissionError) as e:
                log.exception("Error saving configuration", path=str(path), exc_info=e)
