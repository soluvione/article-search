import re
import time
import os
import traceback
from datetime import datetime
import glob
import json
import pprint
import timeit

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from classes.author import Author
# Local imports
from common.erorrs import GeneralError
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

options = Options()
options.page_load_strategy = 'eager'
options.add_argument("--headless")
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

"""
https://comprehensivemedicine.org/
https://eudfd.org/default.aspx
https://jer-nursing.org/


driver.get("https://archivestsc.com/")
article_urls = list()
article_list = driver.find_element(By.CSS_SELECTOR, "table[cellpadding='4']")
rows = article_list.find_elements(By.CLASS_NAME, 'ListArticleTitle')

total_row_num = len(rows)
for row in rows:
    try:
        link = row.get_attribute('href')
        if not link.startswith("https://jag"):
            article_urls.append(link)
    except Exception:
        pass

found_elements = list()
for element in article_list.find_elements(By.TAG_NAME, 'tr'):
    is_found = None
    try:
        is_found = element.find_element(By.CSS_SELECTOR, '.td_pubtype')
        found_elements.append(is_found)
    except:
        pass

for element in found_elements:
    try:
        print(article_list.find_elements(By.TAG_NAME, 'tr').index(element))
    except:
        pass
# TODO hem çirkin hem güzel versiyonlarda linkler düzgün çekiliyor. editorial kapak vs çekilmiyor.
# TODO article type riskli bir şekilde research olacak

print(driver.find_element(By.CSS_SELECTOR, '.badge.badge-danger').text.split('/'))
print(article_urls)
# todo gir içerisine bak abstract yoksa atla sonrakine kafa rahat
print(len(article_urls))
driver.quit()

"""

driver.get("https://archivestsc.com/jvi.aspx?un=TKDA-38141&volume=51&issue=5")
# Abbreviation and DOI
article_data_body = driver.find_element(By.CSS_SELECTOR,
                                        '.col-xs-12.col-sm-9.col-md-9.col-lg-9')

try:
    abbv_doi_element = article_data_body.find_element(By.CSS_SELECTOR,
                                                      ".journalArticleinTitleDOI").text.strip()
    article_doi = abbv_doi_element.split(":")[-1].strip()
    abbreviation = abbv_doi_element[:abbv_doi_element.index(".")].strip()
except Exception as e:
    send_notification(GeneralError(
        f"Error while getting cellpadding4 abbreviationg and DOI of the article: {2} with article num {2}. Error encountered was: {e}"))

# Page range
try:
    first_page = int(
        driver.find_element(By.XPATH, '//meta[@name="citation_firstpage"]').get_attribute(
            'content'))
    last_page = int(
        driver.find_element(By.XPATH, '//meta[@name="citation_lastpage"]').get_attribute('content'))

    article_page_range = [first_page, last_page]
except Exception as e:
    send_notification(GeneralError(
        f"Error while getting cellpadding4 page range data of the article: {2} with article num {2}. Error encountered was: {e}"))

print(abbreviation, article_doi, article_page_range)
# TODO DOI, abb ve range düzgün çekiyor her iki türde de

# Authors
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

# Abstracts
# If there are two abstracts, the second ones should be gotten from Azure services
try:
    abstracts = [element.text.strip() for element in
                 article_data_body.find_elements(By.TAG_NAME, "p")]
except Exception as e:
    send_notification(GeneralError(
        f"Error while getting cellpadding4 article abstracts data of journal: {2} with article num {2}. Error encountered was: {e}"))
    raise e
try:
    h2_elements = article_data_body.find_elements(By.TAG_NAME, "h2")
    for item in h2_elements:
        first_language = "tr"
        if item.get_attribute("class") == "journalArticleinTitleeng":
            first_language = "en"
            break
except Exception as e:
    send_notification(GeneralError(
        f"Error while getting cellpadding4 language order of the article: {2} with article num {2}. Error encountered was: {e}"))

# Keywords
# There are 2 kinds of keywords for cellpadding4 journals. The one acquired from the meta tagged
# elements and the one acquired from the bulk of text
try:
    keywords_element_meta = driver.find_elements(By.CSS_SELECTOR, 'meta[name="keywords"]')
    # get the content attribute of the meta tag
    keywords_text = keywords_element_meta[-1].get_attribute("content")
    keywords_meta = [keyword.strip() for keyword in keywords_text.split(",")]

    soup = BeautifulSoup(article_data_body.get_attribute("innerHTML"), 'html.parser')

    if len(h2_elements) == 2:
        if first_language == "en":
            keyword_element = soup.find('b', string='Anahtar Kelimeler:')
        else:
            keyword_element = soup.find('b', string='Keywords:')
        # Extract the keywords
        keywords_text = keyword_element.find_next_sibling(string=True)
        keywords_last_element = [keyword.strip() for keyword in keywords_text.split(',')]
except Exception as e:
    send_notification(GeneralError(
        f"Error while getting cellpadding4 article keywords data of journal: {2} with article num {2}. Error encountered was: {e}"))

pprint.pprint(keywords_last_element)