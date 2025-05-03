# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import os
import shutil
import stat
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

try:
    import tomli_w as tomlw  # type: ignore[import, unused-ignore]
except ImportError:
    import toml as tomlw  # type: ignore[import, unused-ignore]

from checkconnect.config.settings_manager import SettingsManager


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def settings_manager(temp_config_dir: Path) -> Generator[SettingsManager, None, None]:
    config_path = temp_config_dir / "config.toml"
    original_locations = SettingsManager.CONFIG_LOCATIONS
    SettingsManager.CONFIG_LOCATIONS = [str(config_path)]
    manager = SettingsManager()
    manager.config = manager._load_config()
    yield manager
    SettingsManager.CONFIG_LOCATIONS = original_locations


def test_load_config_from_file(
    settings_manager: SettingsManager,
    temp_config_dir: Path,
) -> None:
    config_path = temp_config_dir / "config.toml"
    config_data = {"test_section": {"test_key": "test_value"}}
    with open(config_path, "wb") as f:
        tomlw.dump(config_data, f)

    settings_manager.config = settings_manager._load_config()
    assert settings_manager.get("test_section", "test_key") == "test_value"


def test_load_config_no_file(
    settings_manager: SettingsManager,
    temp_config_dir: Path,
) -> None:
    config_path = temp_config_dir / "config.toml"
    if config_path.exists():
        os.remove(config_path)

    settings_manager.config = settings_manager._load_config()
    default_level = SettingsManager.DEFAULT_CONFIG["logger"]["level"]
    assert settings_manager.get("logger", "level") == default_level


def test_save_default_config_creates_file(
    settings_manager: SettingsManager,
    temp_config_dir: Path,
) -> None:
    config_path = temp_config_dir / "config.toml"
    if config_path.exists():
        os.remove(config_path)

    settings_manager._save_default_config()
    assert config_path.exists()


def test_get_value_from_config(
    settings_manager: SettingsManager,
    temp_config_dir: Path,
) -> None:
    config_path = temp_config_dir / "config.toml"
    config_data = {"test_section": {"test_key": "test_value"}}
    with open(config_path, "wb") as f:
        tomlw.dump(config_data, f)

    settings_manager.config = settings_manager._load_config()
    assert settings_manager.get("test_section", "test_key") == "test_value"


def test_get_value_default(settings_manager: SettingsManager) -> None:
    default_value = "default"
    result = settings_manager.get(
        "nonexistent_section",
        "nonexistent_key",
        default_value,
    )
    assert result == default_value


def test_load_config_toml_decode_error(
    settings_manager: SettingsManager,
    temp_config_dir: Path,
    capsys,
) -> None:
    config_path = temp_config_dir / "config.toml"
    config_path.write_text("invalid toml", encoding="utf-8")

    config = settings_manager._load_config()
    captured = capsys.readouterr()

    assert "Error reading configuration file" in captured.err or captured.out
    assert config == SettingsManager.DEFAULT_CONFIG


def test_save_default_config_error(
    settings_manager: SettingsManager,
    monkeypatch,
    capsys,
) -> None:
    def mock_dump(*args, **kwargs):
        raise PermissionError("Mocked permission error while writing file")

    monkeypatch.setattr("tomli_w.dump", mock_dump, raising=True)

    settings_manager._save_default_config()

    captured = capsys.readouterr()
    assert "Error writing default configuration" in captured.err or captured.out
