import logging
import logging.handlers



import pytest
from checkconnect.config.logger import ConfiguredLogger


@pytest.fixture(autouse=True)
def patch_settings_manager(mocker):
    """Ensure that SettingsManager is patched before ConfiguredLogger is created."""
    mocked = mocker.patch("checkconnect.config.settings_manager.SettingsManager")
    mocked.return_value.get.side_effect = lambda section, key, default=None: {
        ("logger", "level"): "INFO",
        ("logger", "format"): "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        ("file_handler", "enabled"): False,
        ("limited_file_handler", "enabled"): True,
        ("limited_file_handler", "max_bytes"): 1024 * 1024,
        ("limited_file_handler", "backup_count"): 3,
        ("limited_file_handler", "file_path"): "checkconnect_limited.log",
    }.get((section, key), default)
    return mocked


@pytest.fixture
def configured_logger():
    return ConfiguredLogger()


def test_logger_initialization(configured_logger):
    """Test that the logger is initialized with the correct log level."""
    assert configured_logger._standard_logger.level == logging.INFO


def test_logger_format(configured_logger):
    """Test that the logger is initialized with at least one handler (console)."""
    handlers = configured_logger._standard_logger.handlers
    assert len(handlers) >= 1
    console_handler = next((h for h in handlers if isinstance(h, logging.StreamHandler)), None)
    assert console_handler is not None
    assert "%(asctime)s" in console_handler.formatter._fmt


def test_rotating_file_logging_enabled(configured_logger):
    """Test that the rotating file handler is initialized when enabled."""
    handlers = configured_logger._standard_logger.handlers
    rotating_handler = next(
        (h for h in handlers if isinstance(h, logging.handlers.RotatingFileHandler)),
        None
    )
    assert rotating_handler is not None
    assert rotating_handler.maxBytes == 1024 * 1024
    assert rotating_handler.backupCount == 3
    assert "checkconnect_limited.log" in rotating_handler.baseFilename
