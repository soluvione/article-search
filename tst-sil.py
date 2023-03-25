"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
import time
import os
import glob
from pathlib import Path
import re
# Local imports
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.services.post_json import post_json
from common.services.send_sms import send_notification
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
# 3rd Party libraries
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
download_path = os.path.dirname(os.path.abspath(__file__)) + r'\downloads'
options.add_experimental_option('prefs', {"plugins.always_open_pdf_externally": True})
options.add_experimental_option('prefs', {"download.default_directory": download_path})
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)


url = "https://dergipark.org.tr/tr/pub/hemsire/issue/74622/1213861"

driver.get(url)
author_elements = driver.find_elements(By.CSS_SELECTOR, "p[id*='author']")
for e in author_elements:
    print(e.text)

doi = driver.find_element(By.CSS_SELECTOR, 'a.doi-link').text
print(doi)