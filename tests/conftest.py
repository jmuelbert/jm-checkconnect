# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
import structlog
from PySide6.QtWidgets import QApplication
from typer.testing import CliRunner

from checkconnect.config.appcontext import AppContext
from checkconnect.config.logging_manager import LoggingManager, LoggingManagerSingleton
from checkconnect.config.settings_manager import SettingsManager, SettingsManagerSingleton
from checkconnect.config.translation_manager import TranslationManager, TranslationManagerSingleton

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
    from typing import Literal

    from pytest_mock import MockerFixture
    from structlog.typing import EventDict

@pytest.fixture(scope="function", autouse=True)
def structlog_base_config() -> Generator[None, None, None]:
    root_logger = logging.getLogger()

    root_logger.setLevel(logging.DEBUG) # Important: set root logger level so structlog processes messages

    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    yield
    structlog.reset_defaults()
    root_logger.setLevel(logging.NOTSET)
    logging.disable(logging.NOTSET)
    root_logger.handlers.clear()

@pytest.fixture(scope="function", autouse=True)
def cleanup_singletons() -> Generator[None, None, None]:
    LoggingManagerSingleton._instance = None
    LoggingManager._is_initialized = False
    LoggingManager._instance = None
    SettingsManagerSingleton._instance = None
    TranslationManagerSingleton._instance = None
    LoggingManagerSingleton._initialization_errors.clear()
    yield
    if LoggingManagerSingleton._instance:
        LoggingManagerSingleton.reset()

@pytest.fixture
def caplog_structlog() -> list[EventDict]:
    """
    Captures `structlog` events for the duration of a test.

    This fixture uses `structlog.testing.capture_logs` to collect all log events
    emitted by `structlog` during a test, allowing for assertions on logged content.
    Requires `structlog` to be configured beforehand (e.g., by `structlog_base_config`).

    Returns:
    -------
        A list of `EventDict` objects representing the captured log events.
    """
    with structlog.testing.capture_logs() as captured_events:
        yield captured_events


@pytest.fixture
def assert_log_contains() -> Any:
    """
    Provides a helper function to assert that a `structlog` capture contains specific log entries.

    Returns:
    -------
        A callable that takes `log` (captured events), `text`, and an optional `level`
        to verify the presence of a log entry.
    """

    def _assert(log: list[EventDict], text: str, level: str | None = None) -> None:
        matches = [entry for entry in log if text in entry["event"] and (level is None or entry["level"] == level)]
        assert matches, f"No log entry found with text '{text}' and level '{level}'"

    return _assert


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """
    Creates a temporary test configuration file with predefined content.

    Args:
    ----
        tmp_path: The `pytest` fixture for creating temporary directories.

    Returns:
    -------
        The path to the created temporary configuration file.
    """
    config_content = """
    [logger]
    level = "INFO"
    format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    [file_handler]
    enabled = true
    file_path = "test_checkconnect.log"

    [limited_file_handler]
    enabled = true
    file_path = "test_limited_checkconnect.log"
    max_bytes = 1024
    backup_count = 5

    [general]
    language="en"

    [gui]
    enabled = true

    [reports]
    directory = "test_reports"

    [network]
    timeout = 10
    ntp_servers = [
        "pool.ntp.org"
    ]
    urls = [
        "https://example.com"
    ]
    """
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_config() -> dict[str, Any]:
    """
    Creates a sample configuration dictionary.

    Returns:
    -------
        A dictionary representing a typical application configuration.
    """
    return {
        "logger": {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        },
        "network": {
            "timeout": 5,
            "ntp_servers": [
                "pool.ntp.org",
                "bad-ntp",
            ],
            "urls": [
                "https://example.com" "https://bad-url.invalid",
            ],
        },
        "results": {
            "directory": "test_reports",
        },
    }


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """
    Creates a temporary directory for configuration files and ensures its cleanup.

    Returns:
    -------
        A `pathlib.Path` object pointing to the temporary directory.
    """
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)



@pytest.fixture(autouse=True)
def reset_settings_manager() -> None:
    """
    Resets the `SettingsManagerSingleton` before each test.

    This ensures that each test starts with a clean slate regarding application
    settings, preventing test interdependencies due to shared singleton state.
    """
    SettingsManagerSingleton.reset()


@pytest.fixture
def language() -> str:
    """
    Fixture to return the default language for the application.

    Returns:
    -------
        A string representing the default language, typically "en".
    """
    return "en"


@pytest.fixture
def mocked_translation(mocker: MockerFixture) -> MagicMock:
    """
    Mocks the `gettext.translation` call used within `TranslationManager`.

    This fixture provides a `MagicMock` object that simulates a translation
    object, allowing tests to control and verify translation behavior without
    relying on actual `.mo` files or the `gettext` library.

    Args:
    ----
        mocker: The `pytest-mock` fixture for mocking objects.

    Returns:
    -------
        A `MagicMock` configured to simulate `gettext.translation` and its `gettext` method.
    """
    mocked_gettext = mocker.patch("gettext.translation")
    mock_translation = MagicMock()
    mock_translation.gettext.side_effect = lambda text: f"[mocked] {text}"

    mocked_gettext.return_value = mock_translation

    mocker.patch.object(TranslationManager, "_default_locale_dir", return_value="/mock/locale")
    mocker.patch.object(TranslationManager, "_set_language")

    return mocked_gettext


@pytest.fixture
def mock_translation_manager() -> TranslationManager:
    """
    Returns a `TranslationManager` instance with mocked dependencies.

    This fixture provides a `TranslationManager` ready for testing, where
    its internal `gettext` calls are intercepted by the `mocked_translation` fixture.

    Args:
    ----
        mocked_translation: The `mocked_translation` fixture providing the mocked `gettext`.

    Returns:
    -------
        A `TranslationManager` instance.
    """
    return TranslationManager()


@pytest.fixture
def app_context_fixture(
    mocker: MockerFixture,
    tmp_path: Path,
    request: pytest.FixtureRequest,
) -> AppContext:
    """
    Returns an `AppContext` mock, defaulting to 'full' configuration,
    but can be set to 'simple' via parametrization.

    This fixture allows tests to easily obtain a mock `AppContext` configured
    either minimally ("simple") or with more detailed settings ("full"),
    simulating different application states or configurations.

    Args:
    ----
        mocker: The `pytest-mock` fixture for mocking objects.
        tmp_path: The `pytest` fixture for creating temporary directories.
        request: The `pytest` fixture request object, used to access parametrization.

    Returns:
    -------
        A mocked `AppContext` instance.
    """
    # Determine the desired level: 'simple' if explicitly requested via parametrize,
    # 'full' by default if no parametrization is applied to the fixture request.
    level: Literal["simple", "full"] = (
        request.param if hasattr(request, "param") and request.param is not None else "full"
    )

    # --- Setup the mock logger instance for the AppContext ---
    mock_logger_instance_for_context = mocker.Mock()
    mock_logger_instance_for_context.info.return_value = None
    mock_logger_instance_for_context.warning.return_value = None
    mock_logger_instance_for_context.error.return_value = None
    # Patch structlog.get_logger globally *if* your application code calls it directly
    # and you want to control its return value within tests.
    # If your app always gets loggers via context.get_module_logger, this global patch isn't strictly needed.
    mocker.patch("structlog.get_logger", return_value=mock_logger_instance_for_context)

    mock_translator = mocker.Mock(spec=TranslationManager)
    mock_translator.gettext.side_effect = lambda text: f"[mocked] {text}"
    mock_translator.translate.side_effect = lambda text: f"[mocked] {text}"

    context = mocker.Mock(spec=AppContext)
    context.translator = mock_translator
    context.gettext = mock_translator.gettext
    # Ensure get_module_logger returns the mock logger instance
    context.get_module_logger.side_effect = lambda name: mock_logger_instance_for_context

    # Get a logger *from the context* for messages within the fixture itself
    # This ensures consistency with how your application uses loggers.
    # For fixture-specific internal logging, you might also use a dedicated logger or print statements.
    fixture_logger = context.get_module_logger(__name__)  # Use the logger provided by the mock context

    if level == "simple":
        mock_config = mocker.Mock(spec=SettingsManager)
        mock_config.get_section.return_value.get.return_value = None
        mock_config.get.side_effect = lambda section, key, default=None: (
            default if not (section == "reports" and key == "directory") else None
        )
        context.config = mock_config
        fixture_logger.debug("AppContext fixture providing 'simple' configuration.")
        return context

    # If level is 'full' (either by default or explicitly requested)
    mock_config = mocker.Mock(spec=SettingsManager)

    mock_network_section = mocker.Mock()
    mock_network_section.get.side_effect = lambda key, default=None: {
        "ntp_servers": ["time.google.com", "time.cloudflare.com"],
        "urls": ["https://example.com", "https://google.com"],
        "timeout": 10,
    }.get(key, default)

    def get_section_side_effect(section_name: str) -> MagicMock:
        if section_name == "network":
            return mock_network_section
        return mocker.Mock()

    mock_config.get_section.side_effect = get_section_side_effect

    def config_get_top_level(section: str, key: str, default: Any = None) -> Any:
        if section == "reports" and key == "directory":
            return str(tmp_path / "test_reports_from_config")
        if section == "data" and key == "directory":
            return str(tmp_path / "data")
        if section == "network" and key == "timeout":
            return 10
        return default

    mock_config.get.side_effect = config_get_top_level

    context.config = mock_config
    fixture_logger.debug("AppContext fixture providing 'full' configuration.")
    return context


@pytest.fixture
def mock_network_calls(mocker: MockerFixture) -> None:
    """
    Mocks network-related functionality for isolated testing.

    This fixture patches `ntplib.NTPClient.request` and `requests.get` to
    prevent actual network calls during tests, ensuring fast and reliable
    execution without external dependencies.

    Args:
    ----
        mocker: The `pytest-mock` fixture for mocking objects.
    """
    mock_ntp_response = mocker.Mock()
    mock_ntp_response.tx_time = 1234567890
    mocker.patch("ntplib.NTPClient.request", return_value=mock_ntp_response)

    mock_http_response = mocker.Mock()
    mock_http_response.status_code = 200
    mocker.patch("requests.get", return_value=mock_http_response)


@pytest.fixture
def runner() -> CliRunner:
    """
    Provides an instance of `typer.testing.CliRunner` for testing CLI applications.

    Returns:
    -------
        A `CliRunner` instance.
    """
    return CliRunner()


@pytest.fixture(scope="session")
def q_app() -> Iterator[QApplication]:
    """
    Provides a fresh QApplication instance per test.

    Ensures no QApplication instance leaks across tests.
    Use in GUI-related tests that need QApplication.
    """
    app = QApplication.instance()
    created = False
    if not app:
        app = QApplication([])
        created = True

    yield app

    if created:
        app.quit()
        # Ensure instance is deleted for the next test
        del app


@pytest.fixture
def mock_qapplication_class(mocker: MockerFixture) -> MagicMock:
    """
    Patches QApplication in the startup module so that:
     - QApplication.instance() returns None (forcing creation of a new app)
     - QApplication(sys.argv) returns a MagicMock instance with sane defaults
    Returns the patched constructor mock, so:
        qapp = mock_qapplication_class
        app_instance = qapp.return_value
        app_instance.exec.return_value = <you choose>
    """
    # 1) Create the mocked QApplication *instance*
    mock_app_instance = mocker.MagicMock(spec=QApplication)
    mock_app_instance.exec.return_value = 0
    mock_app_instance.quit.return_value = None

    # 2) Patch the QApplication *class* in your startup module
    mock_qapp_ctor = mocker.patch("checkconnect.gui.startup.QApplication", return_value=mock_app_instance)

    # 3) Ensure .instance() always returns None (so run() will create a new app)
    mock_qapp_ctor.instance.return_value = None

    return mock_qapp_ctor


@pytest.fixture(autouse=True)
def _always_mock_qapp(mock_qapplication_class):
    # this just ensures that every test in this file uses the mock
    return


@pytest.fixture
def sample_ntp_results() -> list[str]:
    """
    Provides sample NTP check results.

    Returns:
    -------
        A list of strings representing example NTP check outcomes.
    """
    return ["NTP Server 1: OK", "NTP Server 2: FAILED"]


@pytest.fixture
def sample_url_results() -> list[str]:
    """
    Provides sample URL check results.

    Returns:
    -------
        A list of strings representing example URL check outcomes.
    """
    return ["https://example.com: OK", "https://bad-url.invalid: ERROR"]


@pytest.fixture(autouse=True)
def mock_dependencies(mocker: MockerFixture) -> dict[str, Any]:
    """
    Mocks external dependencies to isolate the CLI logic during tests.

    This fixture patches modules and classes that perform I/O operations
    (like network checks, file reading, or actual logging configuration)
    to ensure tests are fast, reliable, and independent of external state.

    Args:
    ----
        mocker: The `pytest-mock` fixture for mocking objects.

    Returns:
    -------
        A dictionary containing references to the mocked objects, allowing tests
        to inspect their calls and behavior.
    """

    class MockAbout:
        """A mock class for the __about__ module."""

        __app_name__ = "MockApp"
        __version__ = "0.1.0"

    mocker.patch("checkconnect.__about__", MockAbout())

    def mock_get_option_definition() -> Any:
        """A mock for Typer option definition functions."""
        import typer  # pylint: disable=import-outside-toplevel

        return typer.Option(None)

    mocker.patch("checkconnect.cli.options.get_config_option_definition", return_value=mock_get_option_definition())
    mocker.patch("checkconnect.cli.options.get_language_option_definition", return_value=mock_get_option_definition())
    mocker.patch("checkconnect.cli.options.get_verbose_option_definition", return_value=mock_get_option_definition())

    mock_logging_manager_instance = MagicMock()
    mock_logging_manager_instance.get_logger.return_value = mocker.MagicMock(
        debug=mocker.MagicMock(),
        info=mocker.MagicMock(),
        exception=mocker.MagicMock(),
    )
    mock_logging_manager_singleton = MagicMock()
    mock_logging_manager_singleton.get_instance.return_value = mock_logging_manager_instance
    mocker.patch("checkconnect.config.logging_manager.LoggingManagerSingleton", mock_logging_manager_singleton)

    mock_app_context = MagicMock()
    mock_app_context.gettext.side_effect = lambda x: f"Translated: {x}"
    mocker.patch("checkconnect.cli.run_app.AppContext", return_value=mock_app_context)

    mock_initialize_app_context = mocker.patch(
        "checkconnect.cli.run_app.initialize_app_context", return_value=mock_app_context
    )

    mock_check_connect = MagicMock()
    mock_check_connect.run_all_checks.return_value = None
    mocker.patch("checkconnect.core.checkconnect.CheckConnect", return_value=mock_check_connect)

    return {
        "logging_manager_singleton": mock_logging_manager_singleton,
        "app_context": mock_app_context,
        "initialize_app_context": mock_initialize_app_context,
        "check_connect": mock_check_connect,
        "log_main": mock_logging_manager_instance.get_logger.return_value,
        "log_run_app": mock_logging_manager_instance.get_logger.return_value,
    }
