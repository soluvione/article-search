import pprint
# Python libraries
from datetime import datetime
import time
import os
import glob
import re
import json
from pathlib import Path

from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

import common.helpers.methods.others
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
    abstract_formatter
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
from common.helpers.methods.data_to_atifdizini import get_to_artc_page, paste_data
from common.services.post_json import post_json
from common.services.send_sms import send_notification
from common.services.azure.azure_helper import AzureHelper
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

# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
options.add_argument('--ignore-certificate-errors')
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)


driver.get("https://www.turkhijyen.org/jvi.aspx?un=THDBD-56667&volume=80&issue=2")
time.sleep(5)

# # close button
# try:
#     driver.find_element(By.XPATH, '//*[@id="myModal2"]/div[2]/div/div[3]/button').click()
# except:
#     pass

# Volume and Issue
try:
    vol_issue_text = driver.find_element(By.CLASS_NAME, "kapakYazi").text
except:
    vol_issue_text = driver.find_element(By.CLASS_NAME, "ListArticleIssue").text
numbers = re.findall(r'\d+', vol_issue_text)
numbers = [int(i) for i in numbers]
recent_volume, recent_issue = numbers[:2]
print(recent_volume, recent_issue)

# list
article_list = driver.find_element(By.CSS_SELECTOR, "table[cellpadding='4']")
rows = article_list.find_elements(By.TAG_NAME, ".td_pubtype")
for row in rows:
    print(row.text)


urls = list()
"""
for row in rows:
    links = row.find_elements(By.TAG_NAME, 'a')
    for link in links:
        print(link.get_attribute('href'))
    print("ROW ENDED\n")
"""
# jag test
for row in rows:
    links = row.find_elements(By.TAG_NAME, 'a')
    for link in links:
        if not link.get_attribute('href').startswith("https://jag"):
            urls.append(link.get_attribute('href'))

journal_name = "respiratory CaSes Yeah!"
article_data_body = driver.find_element(By.CSS_SELECTOR, '.col-xs-12.col-sm-9.col-md-9.col-lg-9')

abbv_doi_element = article_data_body.find_element(By.CSS_SELECTOR, ".journalArticleinTitleDOI").text.strip()
doi = abbv_doi_element.split(":")[-1].strip()
abbrv = abbv_doi_element[:abbv_doi_element.index(".")].strip()



h2_elements = article_data_body.find_elements(By.TAG_NAME, "h2")
for item in h2_elements:
    first_language = "tr"
    if item.get_attribute("class") == "journalArticleinTitleeng":
        first_language = "en"
        break

authors_element = article_data_body.find_element(By.CLASS_NAME, "JAgAuthors")
authors_bulk_text = authors_element.text
correspondence_name = authors_element.find_element(By.TAG_NAME, "u").text
authors_list = [author_name.strip() for author_name in authors_bulk_text.split(",")]
# doğru
print(authors_list)
specialities_element = article_data_body.find_element(By.CLASS_NAME, "JAgAffiliations")
# get the HTML of the element
html_string = specialities_element.get_attribute('innerHTML')

# parse the HTML with BeautifulSoup
soup = BeautifulSoup(html_string, 'html.parser')

# remove the <sup> elements
for sup in soup.find_all('sup'):
    sup.decompose()

# separate affiliations by <br> tags and get the text of each affiliation
affiliations = [str(affiliation).strip() for affiliation in soup.stripped_strings]
#print AA NUMARA YOOK FAK

abstracts = [element.text.strip() for element in article_data_body.find_elements(By.TAG_NAME, "p")]


tools_bar_element = driver.find_element(By.CSS_SELECTOR, ".list-group.siteArticleShare")
download_link = tools_bar_element.find_element(By.CSS_SELECTOR, ".list-group-item.list-group-item-toolbox").get_attribute("href")

first_page = int(driver.find_element(By.XPATH, '//meta[@name="citation_firstpage"]').get_attribute('content'))
last_page = int(driver.find_element(By.XPATH, '//meta[@name="citation_lastpage"]').get_attribute('content'))



author_list = list()
for author_name in authors_list:
    author = Author()
    author.name = author_name[:-1] if author_name[-1].isdigit() else author_name
    author.is_correspondence = True if fuzz.ratio(author.name.lower(), correspondence_name.lower()) > 80 else False
    try:
        author.all_speciality = affiliations[int(author_name[-1])-1]
    except ValueError:
        author.all_speciality = affiliations[0]
    author_list.append(author)

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
    """
    # First, try to find the keywords in English
    keyword_element = soup.find('b', string='Keywords:')
    if keyword_element is None:
        # If not found, try to find the keywords in Turkish
        keyword_element = soup.find('b', string='Anahtar Kelimeler:')
    """
    # Extract the keywords
    keywords_text = keyword_element.find_next_sibling(string=True)
    keywords_last_element = [keyword.strip() for keyword in keywords_text.split(',')]


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

article_type = "OLGU SUNUMU" if ("case" in journal_name.lower() or "case" in article_title_eng.lower() or "olgu" in article_title_tr.lower() or "sunum" in article_title_tr.lower() or "bulgu" in article_title_tr.lower()) else "ORİJİNAL ARAŞTIRMA"

driver.quit()

final_article_data = {
    "articleType": article_type,
    "articleDOI": doi,
    "articleCode": abbrv if abbrv else "",
    "articleYear": datetime.now().year,
    "articleVolume": 1,
    "articleIssue": 1,
    "articlePageRange": [first_page, last_page],
    "articleTitle": {"TR": article_title_tr,
                     "ENG": article_title_eng},
    "articleAbstracts": {"TR": abstract_tr,
                         "ENG": abstract_eng},
    "articleKeywords": {"TR": keywords_tr,
                        "ENG": keywords_eng},
    "articleAuthors": author_list,}
pprint.pprint(final_article_data)

"""
import requests
import json

# The URL endpoint
url = "http://178.62.217.122:8080/article/store"

# The request headers
headers = {
    "authorization": "t0U/A2dhjvWuMKkTabbp5IOkXXE2mpfpquMixFFUlTpkwJuOIU93CY=4ftz20-/jUxuxBxW7nqtgWpNf7bJUck6pqGr7=0ZTwA0je6ryUsvYieT?AlPo75TrLiRi0ZBeB/ySwZLfzfB=vjUd4PNx7uAfn?mJ0nL",
}

# Your dictionary
my_dict = {
    "key1": "value1",
    "key2": "value2",
    # Add more keys and values as needed
}

# Convert the dictionary to a JSON string
body = json.dumps(my_dict)

# Make the POST request
response = requests.post(url, headers=headers, data=body)

# Print the response
print(response.json())



import requests
import json

# The URL endpoint
url = "http://178.62.217.122:8080/article/store"

# The request headers
headers = {
    "authorization": "t0U/A2dhjvWuMKkTabbp5IOkXXE2mpfpquMixFFUlTpkwJuOIU93CY=4ftz20-/jUxuxBxW7nqtgWpNf7bJUck6pqGr7=0ZTwA0je6ryUsvYieT?AlPo75TrLiRi0ZBeB/ySwZLfzfB=vjUd4PNx7uAfn?mJ0nL",
}

# Read the JSON data from a file
with open('data.json', 'r') as f:
    body = json.load(f)

# Make the POST request
response = requests.post(url, headers=headers, data=json.dumps(body))

# Print the response
print(response.json())

"""