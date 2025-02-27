import unittest
from configparser import ConfigParser
from unittest.mock import mock_open, patch

from checkconnect.config.settings import Settings


class TestSettings(unittest.TestCase):
    """Unit tests for the Settings class."""

    @patch("builtins.open", new_callable=mock_open, read_data="[default]\nkey=value\n")
    @patch("checkconnect.config.settings.ConfigParser.read")
    def test_settings_initialization(self, mock_read, mock_file):
        """Test that Settings initializes correctly and reads a file."""
        settings = Settings("test.conf")

        mock_read.assert_called_once()
        self.assertEqual(settings.env, "dev")

    @patch("builtins.open", new_callable=mock_open, read_data="[default]\nkey=value\n[dev]\nkey=dev_value\n")
    def test_get_existing_key(self, mock_file):
        """Test that Settings retrieves a value correctly."""
        settings = Settings("test.conf")

        with patch.object(ConfigParser, "read", return_value=None):
            self.assertEqual(settings.get("key"), "dev_value")

    @patch("builtins.open", new_callable=mock_open, read_data="[default]\nkey=value\n")
    def test_get_fallback_default(self, mock_file):
        """Test that Settings falls back to default section if key not found in env section."""
        settings = Settings("test.conf")

        with patch.object(ConfigParser, "read", return_value=None):
            self.assertEqual(settings.get("key"), "value")

    @patch("builtins.open", new_callable=mock_open, read_data="[default]\nkey=value\n")
    def test_get_missing_key(self, mock_file):
        """Test that Settings returns default value when key is missing."""
        settings = Settings("test.conf")

        with patch.object(ConfigParser, "read", return_value=None):
            self.assertEqual(settings.get("non_existent_key", "default_val"), "default_val")

if __name__ == "__main__":
    unittest.main()
