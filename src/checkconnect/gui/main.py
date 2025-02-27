# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

"""
GUI entry point for CheckConnect.

This module serves as the main entry for the GUI version of CheckConnect.
"""

import sys

from PySide6.QtWidgets import QApplication

def gui_main(config_file: str = None, output_file: str = None):
   """
   Main function for launching the CheckConnect GUI.

   This function initializes the logging configuration, creates an instance of
   the CheckConnectGUI class, and starts the GUI application. It handles any
   exceptions that may occur during the startup process and logs them.

   Parameters
   ----------
   config_file (str, optional): The path to the configuration file for the GUI.
                                If None, default settings will be used.
   output_file (str, optional): The path to the output file where results will
                                be saved. If None, results will not be saved.

   Returns
   -------
   None: The function does not return a value. It starts the GUI application.

   """
   logger = logging.getLogger("CheckConnectGUI")  # Create a logger for the GUI
   logger.info("Starting CheckConnect GUI...")  # Log the start of the GUI
   logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

   app = QApplication(sys.argv)
   window = CheckConnectGUI(config_file, output_file)
   window.show()
   sys.exit(app.exec())

    # Set up basic logging configuration

if __name__ == "__main__":
    gui_main()  # Call the main function to start the GUI when the script is executed
