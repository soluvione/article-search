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
options.add_argument("--headless")  # This line enables headless mode
service = ChromeService(executable_path=ChromeDriverManager().install())

# Set start time
start_time = timeit.default_timer()
i = 0  # Will be used to distinguish article numbers
try:
    with webdriver.Chrome(service=service, options=options) as driver:
        # From archives to issue page
        driver.get("https://behcetuzdergisi.com/jvi.asp?pdir=behcetuz&plng=eng&list=pub")
        try:
            main_element = driver.find_element(By.XPATH, '//*[@id="ContentPlaceHolder1_lblContent"]/table')
        except:
            try:
                main_element = driver.find_element(By.XPATH, '//*[@id="ContentPlaceHolder1_ContentPlaceHolder1_lblContent"]/table')
            except:
                main_element = driver.find_element(By.XPATH, '//*[@id="table10"]/tbody/tr/td/table')

        child_element = main_element.find_elements(By.TAG_NAME, 'tr')[2].find_element(By.CLASS_NAME,
                                                                                     'td_parent').find_element(
            By.TAG_NAME, 'tbody')

        issue_link = child_element.find_elements(By.TAG_NAME, 'a')[-1].get_attribute('href')
        numbers = [int(number) for number in re.findall(r'\d+', child_element.text)]
        # Volume, Issue and Year
        recent_volume = numbers[0]
        pattern = r"(: \d+)"
        recent_issue = int(re.findall(pattern, child_element.text)[-1][-1])
        article_year = numbers[1]
        print(recent_volume, recent_issue, issue_link)
except Exception as e:
    print(e)
"""
        main_element = driver.find_element(By.XPATH, '//*[@id="ContentPlaceHolder1_lblContent"]/table')
        child_element = main_element.find_elements(By.TAG_NAME, 'tr')[2].find_element(By.TAG_NAME, 'tbody')
        volume_link = child_element.find_elements(By.TAG_NAME, 'a')[-1].get_attribute('href')
        print(volume_link)
        numbers = [int(number) for number in re.findall('\d+', child_element.find_elements(By.TAG_NAME, 'tr')[-1].text)]
        recent_volume = numbers[0]
        recent_issue = numbers[2]
        year = numbers[1]

        # Issue to urls

        driver.get("https://jarengteah.org/jvi.aspx?pdir=jaren&plng=tur&volume=9&issue=1")
        article_list = driver.find_element(By.CSS_SELECTOR, "table[cellpadding='4']")
        article_urls = list()
        hrefs = [item.get_attribute('href') for item in article_list.find_elements(By.TAG_NAME, 'a')
                 if ("Makale" in item.text or "Abstract" in item.text)]
   
        driver.get("https://agridergisi.com/jvi.aspx?pdir=agri&plng=eng&un=AGRI-46514")



        article_data_body = driver.find_element(By.XPATH, '//*[@id="ContentPlaceHolder1_lblContent"]/table')
        print(driver.find_element(By.XPATH, '//*[@id="ContentPlaceHolder1_lblContent"]/table/tbody/tr[3]/td[2]/table[1]').find_element(By.CSS_SELECTOR, 'a[target="_blank"]').get_attribute('href'))
        doi_abbv_element = driver.find_element(By.CSS_SELECTOR, 'td.tool_j')
        article_code = doi_abbv_element.text.strip().split('.')[0].strip()
        if not article_code:
            article_code = None
        doi = doi_abbv_element.text.split("DOI:")[-1].strip()
        page_range = [int(number.strip()) for number in doi_abbv_element.text[doi_abbv_element.text.index(':')+1: doi_abbv_element.text.index('|')].split('-')]

        try:
            authors_element = article_data_body.find_element(By.CLASS_NAME, "JAgAuthors")
            authors_bulk_text = authors_element.text
            correspondence_name = authors_element.find_element(By.TAG_NAME, "u").text
            authors_list = [author_name.strip() for author_name in authors_bulk_text.split(",")]
            specialities_element = article_data_body.find_element(By.CLASS_NAME, "JAgAffiliations")
            html_string = specialities_element.get_attribute('innerHTML')

            # parse the HTML with BeautifulSoup
            soup = BeautifulSoup(html_string, 'html.parser')

            # remove the <sup> elements
            for sup in soup.find_all('sup'):
                sup.decompose()

            # separate affiliations by <br> tags and get the text of each affiliation
            affiliations = [str(affiliation).strip() for affiliation in soup.stripped_strings]
        except Exception as e:
            send_notification(GeneralError(
                f"Error while getting cellpadding4 article authors' data of journal: {2} with article num {2}. Error encountered was: {e}"))
            raise e

        # Construct Authors List
        author_list = list()
        for author_name in authors_list:
            author = Author()
            author.name = author_name[:-1] if author_name[-1].isdigit() else author_name
            author.is_correspondence = True if fuzz.ratio(author.name.lower(),
                                                          correspondence_name.lower()) > 80 else False
            try:
                author.all_speciality = affiliations[int(author_name[-1]) - 1]
            except ValueError:
                author.all_speciality = affiliations[0]
            author_list.append(author)
        pprint.pprint(author_list)
        abstracts = [element.text.strip() for element in
                     article_data_body.find_elements(By.TAG_NAME, "p")]
        keywords_element_meta = driver.find_elements(By.CSS_SELECTOR, 'meta[name="keywords"]')
        # get the content attribute of the meta tag
        keywords_text = keywords_element_meta[-1].get_attribute("content")
        keywords_meta = [keyword.strip() for keyword in keywords_text.split(",")]

        soup = BeautifulSoup(article_data_body.get_attribute("innerHTML"), 'html.parser')
        h2_elements = article_data_body.find_elements(By.TAG_NAME, "h2")
        first_language = driver.find_element(By.CSS_SELECTOR, 'meta[name="citation_language"]').get_attribute('content')
        if len(h2_elements) == 2:
            if first_language == "en":
                keyword_element = soup.find('b', string='Anahtar Kelimeler:')
            else:
                keyword_element = soup.find('b', string='Keywords:')
            # Extract the keywords
            keywords_text = keyword_element.find_next_sibling(string=True)
            keywords_last_element = [keyword.strip() for keyword in keywords_text.split(',')]
        print(first_language, keywords_last_element, keywords_meta)
        number_of_language = len(h2_elements)
        if number_of_language == 1:
            if first_language == "en":
                article_title_eng = h2_elements[0].text.strip()
                article_title_tr = ""
                abstract_eng = abstracts[0].strip()
                abstract_tr = ""
                keywords_eng = keywords_meta
                keywords_tr = []
            else:
                article_title_eng = ""
                article_title_tr = h2_elements[0].text
                abstract_eng = ""
                abstract_tr = abstracts[0].strip()
                keywords_eng = []
                keywords_tr = keywords_meta
        else:
            if first_language == "en":
                article_title_eng = h2_elements[0].text.strip()
                article_title_tr = h2_elements[1].text.strip()
                abstract_eng = abstracts[0].strip()
                abstract_tr = abstracts[1].strip()
                keywords_eng = keywords_meta
                keywords_tr = keywords_last_element
            else:
                article_title_eng = h2_elements[1].text.strip()
                article_title_tr = h2_elements[0].text.strip()
                abstract_eng = abstracts[1].strip()
                abstract_tr = abstracts[0].strip()
                keywords_eng = keywords_last_element
                keywords_tr = keywords_meta
        print("vur")
"""
