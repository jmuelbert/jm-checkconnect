#
# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2023-present Jürgen Mülbert

"""
CheckConnect CLI Module.

CLI Commands:

    - `gui`: Starts the app in gui mode,
    - `run`: Executes the network connectivity tests.
    - `generate-reports`: Generates the HTML and PDF reports based on the test results.
    - `summary`: Print the summary from the last test result on the console.

Dependencies:

    - `typer`: For the command-line interface (CLI).
    - `rich`: For nice and look well console outputs
    - `checkconnect.core.checkconnect`: For the connectivity checks.
    - `checkconnect.config.appcontext`: For managing application context.
    - `checkconnect.reports.report_generator`: For generating HTML and PDF reports.
    - `checkconnect.reports.report_manager`: For the summary.
    - `checkconnect.gui.gui`: For start the gui mode.
"""
