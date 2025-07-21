from pathlib import Path

import pytest
from typer.testing import CliRunner

from checkconnect.cli.run_app import run_app

runner = CliRunner()

# Angenommen, Sie haben ein Skript namens 'your_app_cli.py'
# und es kann über 'python -m your_app_cli --config config.toml' aufgerufen werden


@pytest.mark.e2e
def test_cli_handles_invalid_config_file(tmp_path: Path):
    invalid_config_file = tmp_path / "invalid_config.toml"
    # Erstelle eine TOML-Datei, die Pydantic als ungültig ablehnen würde
    # z.B. eine ungültige IP oder ein nicht-String-Wert für einen String-Feld
    invalid_config_file.write_text("""
    [ntp]
    servers = ["bad-ntp", 123] # Eine Mischung aus String und Integer, die Pydantic ablehnt
    timeout = 5

    [urls]
    check = ["https://example.com"]
    timeout = 10
    """)

    result = runner.invoke(
        run_app,
        ["--config", str(invalid_config_file), "--language", "en"],
        # KEINE zusätzlichen Argumente wie stderr=True oder catch_exceptions=False hier!
    )

    # WICHTIG: Gib beide Ausgabeströme aus, um zu sehen, wo der Fehler landet
    print("\n--- CLI STDOUT ---")
    print(f"Exit Code: {result.exit_code}")
    print(f"Result   : {result.stdout}")
    print("------------------\n")

    # Prüfe den Exit-Code (muss ungleich 0 sein, da ein Fehler auftrat)
    assert result.exit_code != 0, (
        f"CLI did not exit with error (exit code: {result.exit_code}), STDOUT: {result.stdout}, STDERR: {result.stderr}"
    )

    # Überprüfe, ob die Fehlermeldung in STDOUT oder STDERR enthalten ist
    # Wir müssen beide prüfen, da Typer/Click-Ausgabe manchmal auf stdout landet,
    # auch wenn es ein Fehler ist, oder je nach Logger-Konfiguration.
    error_message_found = False

    # 1. Zuerst STDOUT prüfen
    if "ValidationError" in result.stdout:
        error_message_found = True
        assert "Error configuring NTPChecker" in result.stdout
        # Prüfe auf spezifischere Teile der Pydantic-Fehlermeldung, die in stdout landen könnten
        assert (
            "Value error, Invalid NTP servers: ['bad-ntp', 123]" in result.stdout
            or "List should have at least 1 item after validation" in result.stdout
        )  # Pydantic v1 vs v2 messages

    # 2. Dann STDERR prüfen (wenn der Fehler nicht schon in STDOUT gefunden wurde)
    if not error_message_found:
        try:
            if "ValidationError" in result.stderr:
                error_message_found = True
                assert "Invalid NTP servers" in result.stderr
                # Prüfe auf spezifischere Teile der Pydantic-Fehlermeldung
                assert (
                    "Value error, Invalid NTP servers: ['bad-ntp', 123]" in result.stderr
                    or "List should have at least 1 item after validation" in result.stderr
                )
        except ValueError:
            # Wenn result.stderr einen ValueError wirft, wurde nichts dorthin geschrieben.
            # Der Fehler wurde dann wohl in stdout gefunden (falls error_message_found True ist)
            # oder ist gar nicht aufgetreten (was ein Testfehler wäre).
            pass

    # Am Ende: Stelle sicher, dass die Fehlermeldung irgendwo gefunden wurde
    print(f"Error Message {result.stdout}")
    print(f"Error Message found {error_message_found}")
    assert error_message_found, "Pydantic ValidationError message not found in STDOUT or STDERR."
