import random
import time
import os
import traceback
from datetime import datetime
import glob
import json
import pprint
import timeit
import re
# Local imports
from common.erorrs import GeneralError
from classes.author import Author
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type, reference_formatter
from common.helpers.methods.common_scrape_helpers.other_helpers import check_article_type_pass
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.azure.azure_helper import AzureHelper
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_sms import send_notification
import common.helpers.methods.others
from scrapers.dergipark_scraper import update_scanned_issues
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from fuzzywuzzy import fuzz
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

with_azure = False
with_adobe = False
json_two_articles = False

i = 0
# Webdriver options
# Eager option shortens the load time. Driver also always downloads the pdfs and does not display them
options = Options()
options.page_load_strategy = 'eager'
download_path = ""
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
options.add_argument('--ignore-certificate-errors')
# options.add_argument("--headless")  # This line enables headless mode
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")

# Set start time
start_time = timeit.default_timer()
i = 0  # Will be used to distinguish article numbers

journals = ["https://tjdn.org/index.jsp", "https://tjhealthsport.org/index.jsp", "https://targetmedj.com/index.jsp", "https://anatoljhr.org/index.jsp"]
with webdriver.Chrome(service=service, options=options) as driver:
    driver.get("https://targetmedj.com/index.jsp")
    archives_element = driver.find_element(By.CSS_SELECTOR, 'div[id="sayilar-menusu"]')
    archives_element.find_element(By.CSS_SELECTOR, 'a[class="card-header menu-title head-color special-border1 px-06 collapsed"]').click()
    time.sleep(5)
    driver.maximize_window()
    driver.get('https://anatoljhr.org/index.jsp?mod=tammetin&makaleadi=&makaleurl=8c20ba37-b197-4c9d-a883-b27f9550438d.pdf&key=67055')
    driver.find_element(By.CSS_SELECTOR, 'a[class="btn btn-info"]').click()
    time.sleep(50)