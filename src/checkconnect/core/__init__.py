# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert
#
"""
CheckConnect Module.

This module provides a command-line interface (CLI) for managing network connectivity tests
and generating reports. It tests the connectivity to NTP servers and URLs, and allows the user
to generate HTML and PDF reports based on the results.

The module includes the following features:
- Running network tests for NTP servers and URLs.
- Generating HTML and PDF reports from the results of these tests.
- Using configuration settings from a TOML file.
- Supporting multiple languages for the application.

Classes:
- `CheckConnect`: A class that manages the NTP and URL tests and report generation.

"""
