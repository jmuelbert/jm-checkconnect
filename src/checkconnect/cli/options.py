# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
The common options definitions for the CheckConnect application.
These functions return typer.Option objects to be used with Annotated.
"""

from __future__ import annotations

import typer


# Function to get the language option definition
def get_language_option_definition() -> typer.Option:  # Returns a typer.Option object
    return typer.Option(
        "--language",
        "-l",
        help="Language (e.g., 'en', 'de').",
        rich_help_panel="Localization",
    )


def get_verbose_option_definition() -> typer.Option:
    """
    Returns a typer.Option object for verbosity,
    toggling between INFO and DEBUG.
    """
    return typer.Option(
        "-v",
        "--verbose",
        count=True,  # Typer will count occurrences (0 for default, 1+ for debug)
        help="Increase verbosity. Default logging level is WARNING. Use -v to enable INFO messages. -vv to enable DEBUG messages. Additional -v flags have no further effect.",
        rich_help_panel="Logging",
    )


# Function to get the config file option definition
def get_config_option_definition() -> typer.Option:  # Returns a typer.Option object
    return typer.Option(
        "--config",
        "-c",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the config file. A default one is created if missing.",
        rich_help_panel="Configuration",
    )


# Function to get the reports directory option definition
def get_report_dir_option_definition() -> typer.Option:  # Returns a typer.Option object
    return typer.Option(
        "--reports-dir",
        "-r",
        exists=False,
        file_okay=False,
        dir_okay=True,  # Needs to be True for directories
        readable=True,
        help="Directory where reports will be saved (overrides config).",
        rich_help_panel="Configuration",
    )


# Function to get the data directory option definition
# as default will be use the system-prefered user data dir
def get_data_dir_option_definition() -> typer.Option:  # Returns a typer.Option object
    return typer.Option(
        "--data-dir",
        "-d",
        exists=False,
        file_okay=False,
        dir_okay=True,  # Needs to be True for directories
        readable=True,
        help="Directory where data will be saved. Default used the system defined user data dir.",
        rich_help_panel="Configuration",
    )


# You can add get_data_dir_option_definition similarly
# def get_data_dir_option_definition(...):
#    return typer.Option(...)
