# SPDX-License-Identifier: EUPL-1.2
#
# SPDX-FileCopyrightText: © 2025-present Jürgen Mülbert

import time
from datetime import datetime
import logging
import ntplib
import requests
from fpdf import FPDF

# Set up the logger at the module level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler and set the level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)

def create_pdf_report(ntp_file, url_file):
    """
    Create a PDF report of connectivity tests for NTP servers and URLs.

    This function reads NTP server addresses from a specified file and performs
    time synchronization tests. It also reads URLs from another specified file
    and checks their HTTP status. The results are compiled into a PDF report.

    Parameters
    ----------
    ntp_file (str): The path to the file containing NTP server addresses, one per line.
    url_file (str): The path to the file containing URLs to be tested, one per line.

    Returns
    -------
    None: The function generates a PDF file named 'connectivity_report.pdf'.
    """
    logger.info("Starting PDF report generation.")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=15)
    pdf.cell(200, 10, txt="Connectivity Report", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Erstellt am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='L')

    pdf.cell(200, 10, txt="NTP-Test:", ln=True, align='L')
    with open(ntp_file) as f:
        ntp_servers = [line.strip() for line in f if line.strip()]
    for ntp in ntp_servers:
        try:
            client = ntplib.NTPClient()
            response = client.request(ntp, timeout=5)
            diff = abs(response.tx_time - time.time())
            pdf.cell(200, 10, txt=f"NTP: {ntp} - Zeit: {time.ctime(response.tx_time)} - Abweichung: {diff:.2f}s", ln=True, align='L')
            logger.info(f"NTP: {ntp} - Zeit: {time.ctime(response.tx_time)} - Abweichung: {diff:.2f}s")
        except Exception as e:
            pdf.cell(200, 10, txt=f"Fehler bei NTP {ntp}: {e}", ln=True, align='L')
            logger.error(f"Error retrieving time from NTP server '{ntp}': {e}")

    pdf.cell(200, 10, txt="URL-Test:", ln=True, align='L')
    with open(url_file) as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            pdf.cell(200, 10, txt=f"URL: {url} - Status: {response.status_code}", ln=True, align='L')
            logger.info(f"URL: {url} - Status: {response.status_code}")
        except requests.RequestException as e:
            pdf.cell(200, 10, txt=f"Fehler bei URL {url}: {e}", ln=True, align='L')
            logger.error(f"Error retrieving URL '{url}': {e}")

    pdf.output("connectivity_report.pdf")
    logger.info("PDF report generation completed.")

def create_html_report(ntp_file, url_file):
    """
    Create an HTML report of connectivity tests for NTP servers and URLs.

    This function reads NTP server addresses from a specified file and performs
    time synchronization tests. It also reads URLs from another specified file
    and checks their HTTP status. The results are compiled into an HTML report.

    Parameters
    ----------
    ntp_file (str): The path to the file containing NTP server addresses, one per line.
    url_file (str): The path to the file containing URLs to be tested, one per line.

    Returns
    -------
    None: The function generates an HTML file named 'connectivity_report.html'.
    """
    logger.info("Starting HTML report generation.")
    html_content = f"<html><head><title>Connectivity Report</title></head><body"

    with open(ntp_file) as f:
        ntp_servers = [line.strip() for line in f if line.strip()]
    for server in ntp_servers:
        try:
            client = ntplib.NTPClient()
            response = client.request(ntp, timeout=5)
            diff = abs(response.tx_time - time.time())
            html_content += f"<p>NTP: {server} - Zeit: {ctime(response.tx_time)} - Abweichung: {diff:.2f}s</p>"
        except Exception as e:
            html_content += f"<p>Fehler bei NTP {server}: {e}</p>"

    html_content += "<h2>URL-Test:</h2>"
    with open(url_file) as f:
        urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            html_content += f"<p>URL: {url} - Status: {response.status_code}</p>"
        except requests.RequestException as e:
            html_content += f"<p>Fehler bei URL {url}: {e}</p>"

        html_content += "</body></html>"

        with open("connectivity_report.html", "w") as f:
            f.write(html_content)

    # Example usage:
    # create_pdf_report("ntp_servers.txt", "urls.txt")
    # create_html_report("ntp_servers.txt", "urls.txt")
