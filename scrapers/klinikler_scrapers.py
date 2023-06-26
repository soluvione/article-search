"""
This is the template scraper that will be used to multiply.
"""

# Python libraries
from datetime import datetime
import time
import timeit
import os
from datetime import datetime
import json
import random
import glob
import re
import json
from pathlib import Path
import pprint
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
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter, get_correspondance_name
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
from common.helpers.methods.data_to_atifdizini import get_to_artc_page, paste_data
from common.services.post_json import post_json
from common.services.send_sms import send_notification
from common.services.azure.azure_helper import AzureHelper
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_sms import send_notification, send_example_log
import common.helpers.methods.others
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
# Scraper body chunks
from common.helpers.methods.scraper_body_components import dergipark_components

def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "dergipark_manual", parent_type,
                                  file_reference, "downloads")
    return downloads_path

def klinikler_no_ref_scraper(parent_type, file_reference):

    # Webdriver options
    # Eager option shortens the load time. Always download the pdfs and does not display them.
    options = Options()
    options.page_load_strategy = 'eager'
    # download_path = get_downloads_path(parent_type, file_reference)
    download_path = "/home/emin/Desktop/tk_downloads"
    prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--disable-notifications")
    options.add_argument("--headless")  # This line enables headless mode
    service = ChromeService(executable_path=ChromeDriverManager().install())
    with webdriver.Chrome(service=service, options=options) as driver:
        driver.get("https://www.turkiyeklinikleri.com/journal/endokrinoloji-ozel-konular/89/issue/2023/16/1-0/konjenital-adrenal-hiperplaziler/tr-index.html")
        # time.sleep(1.25)
        # volume_items = driver.find_element(By.ID, 'volumeList')
        # latest_issue = volume_items.find_elements(By.CLASS_NAME, 'issue')[0]
        # issue_no = latest_issue.find_element(By.CLASS_NAME, 'issueNo').text
        if 2 < 4: # check scan
            # issue_link = latest_issue.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
            article_urls = []
            article_list = driver.find_element(By.ID, 'articleList')
            article_elements = article_list.find_elements(By.ID, 'article')
            for item in article_elements:
                if not item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').text.strip() == "ÖN SÖZ":
                    article_urls.append(item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').get_attribute('href'))
                    # print(item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').text)
                    # print(item.find_element(By.CSS_SELECTOR, '.middle .name .nameSub').text)
            # login_button_xpath = driver.find_element(By.XPATH, '/html/body/div/section/div[2]/div[1]/div/a[1]')
            # login_button_xpath.click()
            # time.sleep(3)
            # username_xpath = driver.find_element(By.XPATH, '//*[@id="tpl_login_username"]')
            # username_xpath.send_keys('eminens06@gmail.com')
            # time.sleep(1)
            # password_xpath = driver.find_element(By.XPATH, '//*[@id="tpl_login_password"]')
            # password_xpath.send_keys('h9quxA0vCx')
            # time.sleep(1)
            # confirm_button_xpath = driver.find_element(By.XPATH, '//*[@id="tpl_login_submit"]')
            # confirm_button_xpath.click()
            # time.sleep(7)
            # driver.get(issue_link)
            # time.sleep(7)

            for url in article_urls:
                driver.get(url)
                # time.sleep(5)
                article_element = driver.find_element(By.ID, 'article')
                turkish_title = article_element.find_element(By.CLASS_NAME, 'nameMain').get_attribute('innerHTML')
                english_title = article_element.find_element(By.CLASS_NAME, 'nameSub').get_attribute('innerHTML')
                authors_element = article_element.find_element(By.CLASS_NAME, 'author')
                # print(authors_element.text[: authors_element.text.find('\n')])
                author_names_list = [author.strip() for author in authors_element.text[: authors_element.text.find('\n')].split(',')]
                author_specialities = [speciality for speciality in authors_element.text.split('\n')[1:]]
                abstract_keywords_tr = article_element.find_element(By.CLASS_NAME, 'summaryMain').text
                print(abstract_keywords_tr[abstract_keywords_tr.index('\n'): abstract_keywords_tr.index('Anahtar Kelimeler')].strip())
if __name__ == '__main__':
    klinikler_no_ref_scraper('foo', 'bar')


