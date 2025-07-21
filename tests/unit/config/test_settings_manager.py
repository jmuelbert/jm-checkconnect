# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
Pytest-mock test suite for the SettingsManager class.

This module contains comprehensive tests for the SettingsManager, ensuring its
correct behavior for loading, accessing, and persisting configuration settings.
It uses pytest-mock for mocking file system interactions, TOML parsing,
and other external dependencies.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, call, mock_open, patch

import pytest
import tomli_w

# Assuming SettingsManager and its exceptions are in a file named `settings_manager.py`
# Adjust the import path if your file structure is different.
from checkconnect.config.settings_manager import (
    SettingsConfigurationError,
    SettingsManager,
    SettingsManagerSingleton,
    SettingsWriteConfigurationError,
)

if TYPE_CHECKING:
    from structlog.typing import EventDict

# --- Fixtures ---


@pytest.fixture
def mock_toml_libs(mocker: Any) -> dict[str, MagicMock]:
    """
    Fixture to mock tomllib.load and tomli_w.dump.

    Returns:
        dict[str, MagicMock]: Mocks for tomllib.load and tomli_w.dump.
    """
    mock_tomllib_load = mocker.patch("tomllib.load")
    mock_tomli_w_dump = mocker.patch("tomli_w.dump")
    return {
        "load": mock_tomllib_load,
        "dump": mock_tomli_w_dump,
    }


@pytest.fixture
def mock_importlib_files(mocker: Any, tmp_path: Path) -> Path:
    """
    Fixture to mock importlib.resources.files to return a Path object.
    """
    mock_resource_path = tmp_path / "resources"
    mock_resource_path.mkdir()
    mocker.patch("importlib.resources.files", return_value=mock_resource_path)
    return mock_resource_path


@pytest.fixture
def mock_platformdirs_paths(mocker: Any, tmp_path: Path) -> dict[str, Path]:
    """
    Fixture to mock platformdirs to return paths within a temporary directory.

    Returns:
        dict[str, Path]: A dictionary containing the mocked user and site config paths.
    """
    mock_user_config_dir = tmp_path / "user_config"
    mock_site_config_dir = tmp_path / "site_config"

    mocker.patch("platformdirs.user_config_dir", return_value=str(mock_user_config_dir))
    mocker.patch("platformdirs.site_config_dir", return_value=str(mock_site_config_dir))

    # Ensure these directories exist for tests that expect them to be writable
    mock_user_config_dir.mkdir(parents=True, exist_ok=True)
    mock_site_config_dir.mkdir(parents=True, exist_ok=True)

    return {
        "user_config": mock_user_config_dir,
        "site_config": mock_site_config_dir,
    }


# --- Tests for SettingsManager ---


class TestSettingsManager:
    """
    Test suite for the SettingsManager class.
    """

    @pytest.fixture(autouse=True)
    def setup_default_config_locations(
        self,
        tmp_path: Path,
        mock_platformdirs_paths: dict[str, Path],
        mock_importlib_files: Path,
        mocker: Any,
    ) -> None:
        """
        Set up the CONFIG_LOCATIONS for each test to use temporary paths.
        """
        # Dynamically set DEFAULT_SETTINGS_LOCATIONS to use tmp_path for predictable behavior
        SettingsManager.DEFAULT_SETTINGS_LOCATIONS = [
            tmp_path / "conf.toml",  # Relative path, will be in current working dir of test
            mock_platformdirs_paths["user_config"] / SettingsManager.CONF_NAME,
            mock_platformdirs_paths["site_config"] / SettingsManager.CONF_NAME,
            mock_importlib_files / SettingsManager.CONF_NAME,
        ]
        # Ensure the default config file exists in the mocked resource path for some tests
        # (mock_importlib_files / SettingsManager.CONF_NAME).write_text("dummy_content = 'default'")
        # Mock Path.exists for the initial "config.toml" in current dir
        # mocker.patch.object(Path(SettingsManager.CONFIG_LOCATIONS[0]), "exists", return_value=False)

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_loads_default_if_no_file_found(
        self,
        tmp_path: Path,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsManager loads default configuration if no file is found.
        """

        manager = SettingsManager()

        # Assert that the loaded configuration is indeed the default one
        assert manager.config == SettingsManager.DEFAULT_CONFIG

        assert manager.loaded_config_file == SettingsManager.CONFIG_LOCATIONS[0]

        # If there's a log message about *not* finding a file, you might assert that too.
        # Your previous log assertion about "Default configuration written to" should
        # now be removed or moved to a test specifically for that behavior if it exists elsewhere.
        assert any(
            entry.get("log_level") == "warning"
            and entry.get("event") == "No configuration file found; using default settings."
            for entry in caplog_structlog
        )

        assert any("Default configuration written successfully." in entry["event"] for entry in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_loads_from_specified_file(
        self,
        tmp_path: Path,
        mock_toml_libs: dict[str, MagicMock],
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsManager loads configuration from a specified file.
        """
        test_config_path = tmp_path / "custom_config.toml"
        test_config_path.write_text("[test]\nkey = 'value'")  # Create a dummy file

        assert test_config_path.exists()  # Only test_config_path exists

        mock_toml_libs["load"].return_value = {"test": {"key": "value"}}

        manager = SettingsManager(config_file=test_config_path)

        assert manager.config == {"test": {"key": "value"}}
        mock_toml_libs["load"].assert_called_once()

        assert any(
            entry.get("log_level") == "info"
            and entry.get("event") == "Attempting to load configuration from specified path"
            for entry in caplog_structlog
        )

        assert any(
            entry.get("log_level") == "info" and entry.get("event") == "Loading configuration"
            for entry in caplog_structlog
        )

        assert manager.loaded_config_file == test_config_path

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_handles_default_config_write_failure(
        self,
        mocker: Any,
        tmp_path: Path,
        mock_platformdirs_paths: dict[str, Path],
        mock_importlib_files: Path,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsManager still uses default config if writing it fails.
        """
        # Simulate a write error (e.g., PermissionError when trying to open for writing)
        # Setup: simulate that the first location is not writable
        first_location = Path("/unwritable/config.toml")
        second_location = tmp_path / "config.toml"
        third_location = mock_platformdirs_paths["site_config"] / SettingsManager.CONF_NAME
        fourth_location = mock_importlib_files / SettingsManager.CONF_NAME

        SettingsManager.CONFIG_LOCATIONS = [
            first_location,
            second_location,
            third_location,
            fourth_location,
        ]

        # Patch only the `write_text` for the first path to simulate a failure
        original_write_text = Path.write_text

        def patched_write_text(self: Path, *args: Any, **kwargs: Any) -> None:
            if self == first_location:
                raise PermissionError("Mocked permission denied")
            return original_write_text(self, *args, **kwargs)

        mocker.patch("pathlib.Path.write_text", side_effect=patched_write_text)

        manager = SettingsManager()
        # Config should still be the default, even if writing failed
        assert manager.config == SettingsManager.DEFAULT_CONFIG
        assert manager.loaded_config_file == SettingsManager.CONFIG_LOCATIONS[1]

        for entry in caplog_structlog:
            print(entry)  # Verify specific error logging

        assert any(
            entry["log_level"] == "warning"
            and "Unable to write default configuration to this location, trying next" in entry["event"]
            and "[Errno 30] Read-only file system:" in entry["error"]
            for entry in caplog_structlog
        )
        # Verify no success message about writing the default
        assert not any("Default configuration written to" in entry["event"] for entry in caplog_structlog)

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_loads_from_first_available_location(
        self,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsManager loads from the first existing file in CONFIG_LOCATIONS.
        """
        # Make the user config path exist and contain valid TOML
        first_existing_path = SettingsManager.CONFIG_LOCATIONS[1]  # user_config_dir path

        config_path = Path(first_existing_path)
        with config_path.open("wb") as f:
            f.write(b'[user]\nsetting = "user_value"')

        manager = SettingsManager()

        assert manager.config == {"user": {"setting": "user_value"}}

        assert any(
            entry.get("log_level") == "info" and entry.get("event") == "Loading configuration"
            for entry in caplog_structlog
        )

        assert manager.loaded_config_file == first_existing_path

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_raises_config_file_not_found_error_for_specified_file(
        self,
        mocker: Any,
        tmp_path: Path,
        caplog_structlog: list[EventDict],
        # If mock_structlog_for_settings_manager is a fixture, you need to pass it here:
        # mock_structlog_for_settings_manager: dict[str, MagicMock],
    ) -> None:
        """
        Test that ConfigFileNotFoundError is raised if a specified config_file does not exist.
        """
        non_existent_path = tmp_path / "non_existent.toml"

        # This assertion is good to confirm your test setup: the file genuinely doesn't exist
        assert non_existent_path.exists() is False

        # Mock the 'open' method of the pathlib.Path class
        # This will affect all Path.open calls within the scope of this test
        # Ensure your SettingsManager uses pathlib.Path.open() internally
        mocker.patch("pathlib.Path.open", side_effect=OSError("No such file or directory"))

        # Now, when SettingsManager tries to open `non_existent_path`, its `open` method will
        # raise the OSError, simulating the "file not found" condition at the IO level.
        with pytest.raises(SettingsWriteConfigurationError) as excinfo:
            SettingsManager(config_file=non_existent_path)

        # Assert that an exception log message indicates the configuration file was not found.
        # If you're using caplog_structlog for all log assertions, it's better to use it consistently:
        assert any(
            entry.get("log_level") == "warning"  # or 'exception' depending on how you map structlog levels
            and entry.get("event") == "No configuration file found; using default settings."
            for entry in caplog_structlog
        )
        # You might also want to check for the path in the log context if your logger adds it.
        assert any(
            entry.get("log_level") == "warning"
            and entry.get("event") == "Unable to write default configuration to this location, trying next."
            for entry in caplog_structlog
        )
        # You might also want to check for the path in the log context if your logger adds it.
        assert any(
            entry.get("log_level") == "error"
            and entry.get("event") == "Failed to write default configuration to any specified location."
            for entry in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_raises_settings_configuration_error_on_toml_decode_error(
        self,
        mocker: Any,
        tmp_path: Path,
        mock_toml_libs: dict[str, MagicMock],
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsConfigurationError is raised for invalid TOML syntax.
        """
        invalid_toml_path = tmp_path / "invalid.toml"
        invalid_toml_path.write_text("key = [")  # Invalid TOML

        # Mock the 'open' method of the pathlib.Path class
        # This will affect all Path.open calls within the scope of this test
        # Ensure your SettingsManager uses pathlib.Path.open() internally
        assert invalid_toml_path.exists()

        mock_toml_libs["load"].side_effect = tomllib.TOMLDecodeError("Invalid TOML", 0, 0)

        with pytest.raises(SettingsConfigurationError) as excinfo:
            SettingsManager(config_file=invalid_toml_path)

        # Assert that an exception log message indicates the configuration file was not found.
        # If you're using caplog_structlog for all log assertions, it's better to use it consistently:
        assert any(
            entry.get("log_level") == "error"  # or 'exception' depending on how you map structlog levels
            and entry.get("event") == "TOML decoding failed for configuration file"
            and entry.get("path") == str(invalid_toml_path)
            for entry in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_init_raises_settings_configuration_error_on_generic_load_error(
        self,
        mocker: Any,
        tmp_path: Path,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsConfigurationError is raised for other unexpected loading errors.
        """
        error_path = tmp_path / "error.toml"
        error_path.write_text("some_content")

        assert error_path.exists()

        with pytest.raises(SettingsConfigurationError) as excinfo:
            SettingsManager(config_file=error_path)

        # Assert that an exception log message indicates the configuration file was not found.
        # If you're using caplog_structlog for all log assertions, it's better to use it consistently:
        assert any(
            entry.get("log_level") == "error"  # or 'exception' depending on how you map structlog levels
            and entry.get("event") == "TOML decoding failed for configuration file"
            and entry.get("path") == str(error_path)
            for entry in caplog_structlog
        )

    def test_get_method_existing_value(self) -> None:
        """
        Test get method returns existing value.
        """
        manager = SettingsManager(config_file=None)  # Use default config
        manager.config = {"section": {"key": "value"}}  # Override for test

        assert manager.get("section", "key") == "value"

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_get_method_non_existing_value_with_default(self) -> None:
        """
        Test get method returns default for non-existing value.
        """
        manager = SettingsManager(config_file=None)
        manager.config = {"section": {"key": "value"}}

        assert manager.get("section", "non_existent_key", default="default_value") == "default_value"

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_get_method_non_existing_value_no_default(self) -> None:
        """
        Test get method returns None for non-existing value without default.
        """
        manager = SettingsManager(config_file=None)
        manager.config = {"section": {"key": "value"}}

        assert manager.get("section", "non_existent_key") is None

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_get_section_method_existing_section(self) -> None:
        """
        Test get_section method returns existing section.
        """
        manager = SettingsManager(config_file=None)
        manager.config = {"section": {"key": "value", "another_key": 123}}

        assert manager.get_section("section") == {"key": "value", "another_key": 123}

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_get_section_method_non_existing_section(self) -> None:
        """
        Test get_section method returns empty dict for non-existing section.
        """
        manager = SettingsManager(config_file=None)
        manager.config = {"section": {"key": "value"}}

        assert manager.get_section("non_existent_section") == {}

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_as_dict_method(self) -> None:
        """
        Test as_dict method returns the full config dictionary and that it's a copy.
        """
        manager = SettingsManager(config_file=None)
        # Set the config *after* initialization to ensure it's the specific dict you want to test
        manager.config = {"section": {"key": "value"}}

        # First, assert that the *contents* are equal
        assert manager.as_dict() == {"section": {"key": "value"}}

        # Second, assert that the returned object is *not* the same object in memory
        # as the internal 'config' attribute. This verifies it's a copy.
        assert manager.as_dict() is not manager.config

        # Optional: Verify that modifying the returned dict does not modify the internal config
        returned_dict = manager.as_dict()
        returned_dict["section"]["new_key"] = "new_value"

        assert "new_key" not in manager.config["section"]  # This works with shallow copy for top-level keys

        # If you changed a nested dict:
        returned_dict["section"]["key"] = "modified_value"
        # With a shallow copy, this will *still* modify manager.config["section"]["key"]
        # because the nested dict {"key": "value"} itself is still the same object.
        # To prevent this, you would need a deep copy in as_dict().

        # If your expectation is that modifying nested dicts returned by as_dict()
        # *should not* affect the internal config, then you need `copy.deepcopy` in `as_dict`.
        # If a shallow copy is sufficient (i.e., you only care about top-level dict identity),
        # then the current test with `is not` is fine.
        # Should be a copy or original, but not a deep copy. It is the original.

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_copy_method_returns_deep_copy(self) -> None:
        """
        Test copy method returns a deep copy of the config.
        """
        manager = SettingsManager(config_file=None)
        manager.config = {"section": {"key": "value", "list_key": [1, 2]}}

        copied_config = manager.copy()
        assert copied_config == manager.config
        assert copied_config is not manager.config  # Not the same object
        assert copied_config["section"] is not manager.config["section"]  # Not the same nested dict
        assert (
            copied_config["section"]["list_key"] is not manager.config["section"]["list_key"]
        )  # Not the same nested list

        # Modify copy and ensure original is unchanged
        copied_config["section"]["key"] = "new_value"
        copied_config["section"]["list_key"].append(3)
        assert manager.config["section"]["key"] == "value"
        assert manager.config["section"]["list_key"] == [1, 2]

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_set_method_updates_and_saves(
        self,
        mocker: Any,
        mock_toml_libs: dict[str, MagicMock],
        tmp_path: Path,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that SettingsManager.set() updates a value and saves the config.
        """
        config_file = tmp_path / "config.toml"
        initial_data = {"section": {"key": "old"}}
        with config_file.open("wb") as f:
            tomli_w.dump(initial_data, f)

        # Mocks
        mock_file_read = mock_open()
        mock_file_write = mock_open()

        # Patch global open for tomli/tomli_w
        mocker.patch("builtins.open", mock_file_read)
        mock_toml_libs["load"].return_value = initial_data

        # Patch pathlib.Path.open (all Path.open calls!)
        def path_open_side_effect(self, mode="r", *args, **kwargs):
            if mode == "rb":
                return mock_file_read()
            if mode == "wb":
                return mock_file_write()
            raise ValueError(f"Unexpected open mode: {mode}")

        mocker.patch("pathlib.Path.open", path_open_side_effect)
        mocker.patch("pathlib.Path.mkdir", return_value=None)

        # Act
        manager = SettingsManager(config_file=config_file)
        manager.set("section", "key", "new")

        # Assert
        assert manager.config == {"section": {"key": "new"}}

        dumped_data, file_obj = mock_toml_libs["dump"].call_args[0]
        assert dumped_data == {"section": {"key": "new"}}

        assert any(
            entry.get("log_level") == "info"
            and entry.get("event") == "Attempting to load configuration from specified path"
            and entry.get("path") == str(config_file)
            for entry in caplog_structlog
        )

        assert any(
            entry.get("log_level") == "info" and entry.get("event") == "Loading configuration"
            for entry in caplog_structlog
        )

        assert any(
            entry.get("event") == "Set config value"
            and entry.get("section") == "section"
            and entry.get("key") == "key"
            and entry.get("value") == "new"
            for entry in caplog_structlog
        )
        assert any(
            entry.get("event") == "Configuration saved successfully." and entry.get("path") == str(config_file)
            for entry in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_reload_method(
        self,
        mocker: Any,
        mock_toml_libs: dict[str, MagicMock],
        tmp_path: Path,
    ) -> None:
        """
        Test reload method reloads configuration from disk.
        """
        mock_config_path = Path("mock_config.toml")

        # Initial load
        mock_toml_libs["load"].return_value = {"initial": {"setting": "value"}}
        manager = SettingsManager(config_file=mock_config_path)
        assert manager.config == {"initial": {"setting": "value"}}

        # Simulate change on disk and reload
        mock_toml_libs["load"].return_value = {"reloaded": {"setting": "new_value"}}
        manager.reload()

        assert manager.config == {"reloaded": {"setting": "new_value"}}
        assert mock_toml_libs["load"].call_count == 2  # Called once for init, once for reload

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_save_method_persists_config(
        self,
        mocker: Any,
        mock_toml_libs: dict[str, MagicMock],
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that save() persists the in-memory config to disk.
        """
        # Prepare path and initial config
        mock_config_path = Path("mock_config.toml")
        initial_data = {"test": {"key": "value"}}
        mock_toml_libs["load"].return_value = initial_data

        # Mock the file handle returned by Path.open("wb")
        mock_file_handle = MagicMock()
        mock_open = mocker.patch("pathlib.Path.open", return_value=mock_file_handle)
        mocker.patch("pathlib.Path.mkdir", return_value=None)

        # Instantiate and prepare manager
        manager = SettingsManager(config_file=mock_config_path)
        manager.loaded_config_file = mock_config_path

        # Modify config directly
        manager.config["test"]["key"] = "modified_value"

        # Call save
        manager.save()

        # ✅ Assert tomli_w.dump was called with correct arguments
        # Assert tomli_w.dump was called with correct arguments
        mock_toml_libs["dump"].assert_called_once_with(manager.config, mock_file_handle.__enter__())

        # ✅ Optionally: check that Path.open was called correctly
        # Confirm it was called with 'wb' at least once
        assert call("wb") in mock_open.call_args_list

        # ✅ Check log message
        assert any(
            record["event"] == "Configuration saved successfully." and record.get("path") == str(mock_config_path)
            for record in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_save_method_no_writable_location(
        self,
        mocker: Any,
        mock_toml_libs: dict[str, MagicMock],
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test that save() logs an error if no writable location is found.
        """
        # Patch Path.exists to simulate no config file was loaded
        mocker.patch("pathlib.Path.exists", return_value=False)

        # Patch Path.mkdir and Path.open to raise PermissionError (simulating unwritable locations)
        mocker.patch("pathlib.Path.mkdir", side_effect=PermissionError("No write access"))
        mocker.patch("pathlib.Path.open", side_effect=PermissionError("No write access"))

        with pytest.raises(SettingsWriteConfigurationError) as excinfo:
            # Attempt to save (should fail and log error)
            # Instantiate manager without specifying config_file (will use default search paths)
            manager = SettingsManager()

            # Explicitly remove loaded_config_file to trigger writable search fallback
            manager.loaded_config_file = None

            manager.save()

        # Confirm: tomli_w.dump should not be called
        mock_toml_libs["dump"].assert_not_called()

        for entry in caplog_structlog:
            print(entry)

        # Confirm: error was logged
        assert any(
            record["event"] == "No configuration file found; using default settings."
            and record["log_level"] == "warning"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "Unable to write default configuration to this location, trying next."
            and record["log_level"] == "warning"
            for record in caplog_structlog
        )

        assert any(
            record["event"] == "Failed to write default configuration to any specified location."
            and record["log_level"] == "error"
            for record in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_save_default_config_success(
        self,
        mocker: Any,
        mock_toml_libs: dict[str, MagicMock],
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test _save_default_config successfully writes the default configuration.
        """
        # Patch Path.exists to simulate no config file was loaded
        # mocker.patch("pathlib.Path.exists", return_value=False)

        # # Patch Path.mkdir and Path.open to raise PermissionError (simulating unwritable locations)
        # mocker.patch("pathlib.Path.mkdir", side_effect=PermissionError("No write access"))
        # mocker.patch("pathlib.Path.open", side_effect=PermissionError("No write access"))

        SettingsManager()  # This will trigger _save_default_config

        mock_toml_libs["dump"].assert_called()

        for entry in caplog_structlog:
            print(entry)

        assert any(
            record["log_level"] == "info"
            and record["event"] == "Default configuration written successfully."
            and record["path"] == str(SettingsManager.CONFIG_LOCATIONS[0])  # First writable path
            for record in caplog_structlog
        )

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_save_default_config_raises_settings_write_configuration_error(
        self,
        mocker: Any,
        caplog_structlog: list[EventDict],
    ) -> None:
        """
        Test _save_default_config raises SettingsWriteConfigurationError if writing fails.
        """
        # Patch Path.exists to simulate no config file was loaded
        mocker.patch("pathlib.Path.exists", return_value=False)

        # Patch Path.mkdir and Path.open to raise PermissionError (simulating unwritable locations)
        mocker.patch("pathlib.Path.mkdir", side_effect=OSError("Cannot create dir"))
        mocker.patch("pathlib.Path.open", side_effect=OSError("Disk full"))

        with pytest.raises(SettingsWriteConfigurationError) as excinfo:
            SettingsManager()

        for entry in caplog_structlog:
            print(entry)

        assert any(
            record["log_level"] == "error"
            and record["event"] == "Failed to write default configuration to any specified location."
            for record in caplog_structlog
        )

        print(excinfo.value)
        assert "Could not save default configuration to any valid location." in str(excinfo.value)


class TestSettingsManagerSingleton:
    """
    Test suite for the SettingsManagerSingleton class.
    """

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    def test_get_instance_creates_and_returns_single_instance(
        self,
    ) -> None:
        """
        Test get_instance creates a new instance on first call and returns the same on subsequent calls.
        """
        # Ensure default config is loaded without errors

        first_instance = SettingsManagerSingleton.get_instance()
        second_instance = SettingsManagerSingleton.get_instance()

        assert first_instance is second_instance

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_clears_instance(self) -> None:
        """
        Test that reset sets the _instance to None.
        """
        # Ensure an instance exists
        instance = SettingsManagerSingleton.get_instance()
        assert instance is not None

        # Call the reset method
        SettingsManagerSingleton.reset()

        # Assert that the instance is now None
        assert SettingsManagerSingleton._instance is None  # noqa: SLF001

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons", "structlog_base_config")
    @patch("checkconnect.config.settings_manager.SettingsManager")
    def test_reset_and_new_instance(self, mock_settings_manager_cls: MagicMock) -> None:
        """
        Test reset method clears the singleton instance.
        """

        mock_instance_1 = MagicMock(name="FirstSettingsManager")
        mock_instance_2 = MagicMock(name="SecondSettingsManager")

        # Ensure each call to LoggingManager() gives a new instance
        mock_settings_manager_cls.side_effect = [mock_instance_1, mock_instance_2]

        first_instance = SettingsManagerSingleton.get_instance()
        assert first_instance is mock_instance_1

        # Reset and get new instance
        SettingsManagerSingleton.reset()
        second_instance = SettingsManagerSingleton.get_instance()
        assert second_instance is mock_instance_2

        # ✅ Main assertion
        assert first_instance is not second_instance

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_initialization_errors(
        self,
    ) -> None:
        """
        Test get_initialization_errors method returns errors during initialization.
        """
        # We need to patch __init__ BEFORE the singleton tries to create an instance.
        # This means patching it within a 'with' statement, and then calling get_instance
        # inside that 'with' statement.

        # The key is that cleanup_singletons should ensure LoggingManagerSingleton
        # is reset, so get_instance() will call __init__ again.
        with (
            patch.object(SettingsManager, "__init__", side_effect=Exception("Mocked error")),
            pytest.raises(Exception, match="Mocked error"),
        ):
            # Call get_instance *inside* the patch context.
            # This will trigger __init__ with the side_effect.
            SettingsManagerSingleton.get_instance()

        # After the exception is caught, you could potentially assert on the instance's errors
        # if the LoggingManager's __init__ was designed to set them even on failure.
        # However, since the Exception propagates, the instance won't be fully initialized.
        # This test primarily validates the exception propagation.

        # If you *also* need to check self.setup_errors, you'd need to catch the exception,
        # and then inspect the *exception object itself* if it contained the instance,
        # or mock the append method to capture what would have been appended.
        # For now, let's focus on the primary failure (exception not raised).

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_reset_clears_initialization_errors(self) -> None:
        """
        Test that reset clears any accumulated initialization errors.
        """
        # Manually add an error to simulate a previous failed initialization
        SettingsManagerSingleton._initialization_errors.append("Simulated init error 1")  # noqa: SLF001
        SettingsManagerSingleton._initialization_errors.append("Simulated init error 2")  # noqa: SLF001

        # Verify errors are present before reset
        assert len(SettingsManagerSingleton.get_initialization_errors()) == 2

        # Call the reset method
        SettingsManagerSingleton.reset()

        # Assert that the errors list is now empty
        assert SettingsManagerSingleton.get_initialization_errors() == []
        assert len(SettingsManagerSingleton.get_initialization_errors()) == 0

    @pytest.mark.unit
    @pytest.mark.usefixtures("cleanup_singletons")
    def test_get_initialization_errors_returns_correct_errors(self) -> None:
        """
        Test get_initialization_errors returns errors during initialization.
        This re-uses the pattern from your previous test problem.
        """
        # Patch LoggingManager's __init__ to raise an error
        expected_error_msg = "Mocked init error for test"
        with patch.object(SettingsManager, "__init__", side_effect=Exception(expected_error_msg)):
            with pytest.raises(Exception, match=expected_error_msg):
                # This call will trigger __init__ which will raise the error
                SettingsManagerSingleton.get_instance()

            # Now, after the exception, check if the error was logged in the singleton
            errors = SettingsManagerSingleton.get_initialization_errors()
            assert len(errors) == 1
            assert expected_error_msg in errors[0]  # Check that the message is part of the error string

        # Ensure cleanup_singletons runs after this test to clear the error for subsequent tests
