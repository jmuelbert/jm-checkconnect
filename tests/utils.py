# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert


class MockLogger:
    """
    Mock class for logging.Logger to capture log messages in tests.

    This class mimics the behavior of the standard logging.Logger class
    but stores the log messages in lists for easy inspection during testing.
    """

    def __init__(self):
        """
        Initializes a new MockLogger with empty lists for different log levels.
        """
        self.messages = []
        self.debugs = []
        self.infos = []
        self.warnings = []
        self.errors = []
        self.exceptions = []

    def debug(self, msg, *args, **kwargs):
        """
        Simulates the debug method of a logger, appending the message to the debugs list.

        Args:
            msg (str): The log message.
            *args: Arguments for the log message.
            **kwargs: Keyword arguments for the log message.
        """
        self.debugs.append(msg % args if args else msg)

    def info(self, msg, *args, **kwargs):
        """
        Simulates the info method of a logger, appending the message to the infos list.

        Args:
            msg (str): The log message.
            *args: Arguments for the log message.
            **kwargs: Keyword arguments for the log message.
        """
        self.infos.append(msg % args if args else msg)

    def warning(self, msg, *args, **kwargs):
        """
        Simulates the warning method of a logger, appending the message to the warnings list.

        Args:
            msg (str): The log message.
            *args: Arguments for the log message.
            **kwargs: Keyword arguments for the log message.
        """
        self.warnings.append(msg % args if args else msg)

    def error(self, msg, *args, **kwargs):
        """
        Simulates the error method of a logger, appending the message to the errors list.

        Args:
            msg (str): The log message.
            *args: Arguments for the log message.
            **kwargs: Keyword arguments for the log message.
        """
        self.errors.append(msg % args if args else msg)

    def exception(self, msg, *args, **kwargs):
        """
        Simulates the exception method of a logger, appending the message to the exceptions list.

        Args:
            msg (str): The log message.
            *args: Arguments for the log message.
            **kwargs: Keyword arguments for the log message.
        """
        self.exceptions.append(msg % args if args else msg)

    def reset(self):
        """
        Resets all message lists to empty, clearing the captured log messages.
        """
        self.messages = []
        self.debugs = []
        self.infos = []
        self.warnings = []
        self.errors = []
        self.exceptions = []
