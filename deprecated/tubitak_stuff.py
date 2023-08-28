# Python libraries
import pprint
import time
import os
import re
import json
import urllib.parse

import requests
from bs4 import BeautifulSoup

import common.helpers.methods.others
# Local imports
from classes.author import Author
from common.erorrs import DownloadError, ParseError, GeneralError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.send_sms import send_notification
from common.services.azure.azure_helper import AzureHelper
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
# Scraper body chunks
from common.helpers.methods.scraper_body_components import dergipark_components
import timeit
# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
options.add_argument("--headless")
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())


urls = ["https://journals.tubitak.gov.tr/veterinary", "https://journals.tubitak.gov.tr/medical"]
with webdriver.Chrome(service=service, options=options) as driver:
    # Bunlar sadece İngilizce
    start_page_url = ""
    driver.get(urls[1])
    issue_page_main_element = driver.find_element(By.ID, 'alpha')
    current_issue_text = issue_page_main_element.find_element(By.TAG_NAME, 'h1').text
    numbers = re.findall('[0-9]+', current_issue_text)
    year = int(numbers[0])
    recent_volume = int(numbers[1])
    recent_issue = int(numbers[2])

    article_elements = driver.find_elements(By.CSS_SELECTOR, 'div[class="doc"]')
    article_urls = list()
    for item in article_elements:
        article_urls.append(item.find_elements(By.TAG_NAME, 'p')[1].find_element(By.TAG_NAME, 'a').get_attribute('href'))
    article_urls = article_urls[1:]

    driver.get("https://journals.tubitak.gov.tr/veterinary/vol47/iss4/2")
    article_title_eng = driver.find_element(By.ID, 'title').text.strip()

    authors_elements = driver.find_element(By.ID, 'authors').find_element(By.TAG_NAME, 'p').find_elements(By.TAG_NAME, 'a')
    author_names = [name.text.strip() for name in authors_elements]

    doi = driver.find_element(By.ID, 'doi').text.strip()
    doi = doi[doi.index("10."):]

    article_abstract_eng = driver.find_element(By.ID, 'abstract').text.strip()

    keywords_eng = driver.find_element(By.ID, "keywords").text.strip().split('\n')[-1]

    page_range = [driver.find_element(By.ID, 'fpage').find_element(By.TAG_NAME, 'p').text,
                  driver.find_element(By.ID, 'lpage').find_element(By.TAG_NAME, 'p').text]


    abbreviation = "Turk J Vet Anim Sci" if "veterinary" in start_page_url else "Turk J Med Sci"

    download_link = driver.find_element(By.CSS_SELECTOR, 'div[class="aside download-button"]').find_element(By.TAG_NAME, 'a').get_attribute('href')


