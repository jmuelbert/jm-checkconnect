# SPDX-FileCopyrightText: © 2023-2024 Jürgen Mülbert
#
# SPDX-License-Identifier: EUPL-1.2

"""Check the connectivity to https: Server_"""

from __future__ import annotations

import csv
import locale
import os
from typing import TYPE_CHECKING, Any, TypeAlias

import requests

if TYPE_CHECKING:
    import fpdf

    BasePathLike = os.PathLike[Any]
else:
    BasePathLike = os.PathLike

FileName: TypeAlias = str | bytes | BasePathLike


def test_urls(url_file: FileName, pdf_output: fpdf) -> None:
    """Tests URLs from a CSV file.

    Args:
    ----
      url_file: Path to CSV file containing URLs to test. URLs
                are assumed to be in the first column.
      pdf_output: PDF file opened for writing to log results.

     For each URL in the CSV file, sends a GET request and
     writes the response status code and content length to
     the PDF file. If an exception occurs, it is caught and
     an error message is written instead.

    """
    # Create a list to store the URLs
    urls = []

    # Open the URL file and read the URLs
    with open(url_file, encoding=locale.getpreferredencoding(False)) as f:
        reader = csv.reader(f)
        for row in reader:
            # Assume the URL is in the first column of the CSV file
            url = row[0]
            # Append the URL to the list
            urls.append(url)

    # Loop through each URL
    for url in urls:
        # Try to get the response from the URL
        try:
            response = requests.get(url, timeout=10)

            # If successful, write the status code and the content length to the PDF file
            pdf_output.write(5, f"URL: {url}\n")
            pdf_output.write(5, f"Status: {response.status_code}\n")
            pdf_output.write(5, f"Content length: {len(response.content)}\n")
            pdf_output.write(5, "\n")

        except requests.exceptions.RequestException as e:
            pdf_output.write(5, f"URL: {url}\n")
            pdf_output.write(5, f"Error: {e}\n")
            pdf_output.write(5, "\n")
