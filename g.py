url = "https://dergipark.org.tr/tr/pub/hacettepesid/issue/76286/1076956"

"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
from datetime import datetime
import time
import os
import glob
import re
from pathlib import Path
# Local imports
from classes.author import Author
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter
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
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path, "detach": True}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

article_url = "https://dergipark.org.tr/tr/pub/abantmedj/issue/74313/1225644"
driver.get(article_url)

el = driver.find_element(By.XPATH, '/html/body/div[2]/div/div/div[3]/div[1]/div[1]/div[1]/div[1]/div/span').text
print(el)

reference_list_elements = driver.find_elements(
                        By.CSS_SELECTOR, 'div.article-citationssdsdds.data-section')

print(len(reference_list_elements))
# test