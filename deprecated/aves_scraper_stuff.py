# Python libraries
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
driver = webdriver.Chrome(service=service, options=options)


# Aves journals' latest issue is on the main page all the time.
# You need to scroll the aves articles down
"""
driver.get("https://www.aott.org.tr/")
time.sleep(10)

# Scroll to the bottom
start = timeit.default_timer()
while timeit.default_timer() - start < 10:
    driver.execute_script("window.scrollBy(0,500)")
    time.sleep(0.2)
# Goes up
driver.execute_script("window.scrollBy(0,-5000)")
driver.maximize_window()
time.sleep(5)

numbers = [int(number) for number in
           re.findall(r'\d+', driver.find_element(By.CSS_SELECTOR, "[class^='article_type_head']").text)]
recent_volume, recent_issue, year = numbers[0], numbers[1], numbers[2]

article_urls = list()
for item in driver.find_elements(By.CSS_SELECTOR, "[class='article']"):
    article_urls.append(item.find_element(By.TAG_NAME, 'a').get_attribute('href'))
    
for article_url in article_urls:
    driver.get(article_url)

"""
# From the article page and so on
driver.get("https://www.aott.org.tr/en/identification-of-risk-factors-for-reconstructive-hip-surgery-after-intrathecal-baclofen-therapy-in-children-with-cerebral-palsy-137312")
time.sleep(5)
driver.find_element(By.CSS_SELECTOR, '.reference.collapsed').click()
time.sleep(5)
# Authors
authors_element = driver.find_element(By.CLASS_NAME, 'article-author')
authors_bulk_text = authors_element.text
authors_list = [author.strip() for author in authors_bulk_text.split(',')]

specialities_bulk = driver.find_element(By.CSS_SELECTOR,
                                        '.reference-detail.collapse.in').text.split('\n')
#  There are number values so need to clean it
for item in specialities_bulk:
    if '.' in item:
        specialities_bulk.pop(specialities_bulk.index(item))
specilities = specialities_bulk

authors = list()
for author_name in authors_list:
    author = Author()
    try:
        author.name = author_name[:-1].strip()
        author.all_speciality = specilities[int(author_name[-1])-1]
        author.is_correspondence = True if authors_list.index(author_name) == 0 else False
        authors.append(author)
    except Exception as e:
        send_notification(GeneralError(
            f"Error while getting aves article authors' data of journal: {e}. Error encountered was: {e}"))
print(authors)
# Type
article_type = identify_article_type(
    driver.find_element(By.CSS_SELECTOR, "[class^='article_type_hea']").text.strip(), 0)
print(article_type)

# Title
article_title = driver.find_element(By.CLASS_NAME, 'article_content').text.strip()

authors_element = driver.find_element(By.CLASS_NAME, 'article-author')
authors_bulk_text = authors_element.text
# print(authors_bulk_text.split(','))

specialities_bulk = driver.find_element(By.CSS_SELECTOR, '.reference-detail.collapse.in').text.split('\n')
#  there are number values so need to clean it
for item in specialities_bulk:
    if '.' in item:
        specialities_bulk.pop(specialities_bulk.index(item))
specilities = specialities_bulk

# abbv. year and page-range data
bulk_text = driver.find_element(By.CSS_SELECTOR, 'div.journal').text
journal_abbv = re.sub(r'\d+|[:.;-]+', '', bulk_text).strip()
page_range = [int(number) for number in bulk_text.split()[-1].split('-')]

doi = driver.find_element(By.CSS_SELECTOR, '.doi').text.split(':')[-1].strip()

keywords = driver.find_element(By.CSS_SELECTOR, '.keyword').text.split(':')[-1].strip().split(',')
keywords = [keyword.strip() for keyword in keywords]

download_link = driver.find_element(By.CLASS_NAME, 'articles').find_element(By.TAG_NAME, 'a').get_attribute('href')

abstract = driver.find_element(By.CSS_SELECTOR, '.content').text.split("Cite this")[0].strip()

# No references available for the aves_scrapers.
