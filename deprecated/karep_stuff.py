# Python libraries
import pprint
import time
import os
import re
import json

import common.helpers.methods.others
# Local imports
from classes.author import Author
from common.errors import DownloadError, ParseError, GeneralError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.send_notification import send_notification
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
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver-linux64/chromedriver")


urls = ["https://hepatologyforum.org", "https://dusunenadamdergisi.org/", "https://eurasianjpulmonol.com/"]
with webdriver.Chrome(service=service, options=options) as driver:
    for url in urls:
        start_page_url = url
        driver.get(start_page_url)
        vol_issue_text = driver.find_element(By.CSS_SELECTOR, 'h1[class="content-title"]').text
        regex = re.findall(r'\d+', vol_issue_text)
        year = regex[2]
        vol = regex[0]
        issue = regex[1]

        article_urls = list()
        article_types = list()
        category_elements = driver.find_elements(By.CSS_SELECTOR, 'div[class="col-12 category-container"]')

        for category_element in category_elements:
            number_to_add = category_element.find_elements(By.CSS_SELECTOR, 'div[class="row article"]')
            category_name = category_element.find_element(By.TAG_NAME, 'h3').text.strip()
            for i in number_to_add:
                article_types.append(category_name)
            url_elements = [element.find_element(By.TAG_NAME, 'a').get_attribute('href') for element in category_element.find_elements(By.CSS_SELECTOR, 'div[class="row article"]')]
            for element in url_elements:
                article_urls.append(element)
        if "Front Matter" in article_types:
            article_types = article_types[1:]
            article_urls = article_urls[1:]

    driver.get("https://dusunenadamdergisi.org/article/1603")
    main_element = driver.find_element(By.CSS_SELECTOR, 'div[class="row article"]')

    article_title_eng = main_element.find_element(By.CLASS_NAME, 'article-title').text.strip()
    article_title_tr = None
    author_names = main_element.find_element(By.CLASS_NAME, 'article-authors').text
    author_affiliations = main_element.find_element(By.CLASS_NAME, 'article-institutions').text

    doi_n_pages_text = main_element.find_element(By.CLASS_NAME, 'article-doi-pages').text
    doi = doi_n_pages_text[doi_n_pages_text.index("DOI:") + 4:].strip()
    page_range_pattern = r"\d+-\d+"
    page_range = [int(page_range) for page_range in re.search(page_range_pattern, doi_n_pages_text).group(0).split('-')]
    print(page_range)

    abstract_eng = main_element.find_element(By.CLASS_NAME, 'article-abstract').text.strip()
    abstract_tr = None

    keywords_eng = main_element.find_element(By.CLASS_NAME, 'article-keywords').text
    keywords_eng = [keyword.strip() for keyword in keywords_eng[keywords_eng.index(":")+1:].split(',')]

    download_link = main_element.find_element(By.CLASS_NAME, 'article-buttons').find_element(By.TAG_NAME, 'a').get_attribute('href')
    print(download_link)
