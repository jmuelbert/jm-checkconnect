# SPDX-FileCopyrightText: © 2023-2024 Jürgen Mülbert
#
# SPDX-License-Identifier: EUPL-1.2

"""Test the main CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from checkconnect.cli import checkconnect


def test_main_succeeds() -> None:
    """
    Test that the main CLI command exits with a status code
    of zero when the --version flag is passed.
    It exits with a status code of zero.
    """
    runner = CliRunner()
    result = runner.invoke(checkconnect, ["--version"])
    assert result.exit_code == 0
