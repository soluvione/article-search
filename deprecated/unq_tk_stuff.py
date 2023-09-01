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
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")

# https://www.journalofoncology.org/
# https://www.jpmrs.org
# https://www.tjrms.org/
urls = ["https://www.tjrms.org/", "https://www.jpmrs.org", "https://www.journalofoncology.org/"]
with webdriver.Chrome(service=service, options=options) as driver:
    for url in urls:
        start_page = url
        driver.get(start_page)
        if not "journalofoncology" in start_page:
            recent_issue_text = driver.find_element(By.CSS_SELECTOR, 'div[class^="issue-details col-md-4"]').text
        else:
            recent_issue_text = driver.find_element(By.CSS_SELECTOR, 'div[class^="issue-bar issue-bar-right"]').text

        numbers = re.findall('[0-9]+', recent_issue_text)
        article_year = int(numbers[0])
        recent_volume = int(numbers[1])
        recent_issue = int(numbers[2])

        article_urls = [element.find_element(By.TAG_NAME, 'a').get_attribute('href') for element in driver.find_elements(By.CSS_SELECTOR, 'span[class="article_name"]')]

        # jpmrs VE tjrms ÇİFT DİLLİ, journalofoncology TEK DİLLİ İNGİLİZCE
    start_page = "https://www.journalofoncology.org/current-issue/prognostic-significance-of-mucinous-histology-in-metastatic-colorectal-cancer-patients-treated-with-regorafenib-223#selectabstract"
    # ARTICLE PAGE PARTS
    driver.get(start_page)
    main_element = driver.find_element(By.CSS_SELECTOR, 'div[class="col-md-12 category-panel"]') if "journalofoncology" in start_page else driver.find_element(By.CSS_SELECTOR, 'div[class="col-md-10"]')

    article_type = main_element.find_element(By.CSS_SELECTOR, 'div[class="bold-medium blue-light-back"]').text if not "journalofoncology" in start_page else driver.find_element(By.CSS_SELECTOR, 'div[class="category-panel-name"]').text.strip()
    article_type = identify_article_type(article_type, 0)

    author_names = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-author"]')[0].text.split(',')
    author_affiliations_data = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-author"]')[1].text
    author_affiliations = list()
    array = [author_affiliations_data.index(found) for found in re.findall('[a-z][A-Z]', author_affiliations_data)]
    for i in range(len(array)):
        try:
            author_affiliations.append(author_affiliations_data[array[i]: array[i+1]][1:])
            i += 1
        except:
            author_affiliations.append(author_affiliations_data[array[-1]:][1:])

    author_object = list()
    for name in author_names:
        author = Author(name=name[:-1])
        try:
            if author.name[-1] == "a":
                author.all_speciality = author_affiliations[0]
            elif author.name[-1] == "b":
                author.all_speciality = author_affiliations[1]
            elif author.name[-1] == "c":
                author.all_speciality = author_affiliations[2]
            elif author.name[-1] == "d":
                author.all_speciality = author_affiliations[3]
            elif author.name[-1] == "e":
                author.all_speciality = author_affiliations[4]
            elif author.name[-1] == "f":
                author.all_speciality = author_affiliations[5]
            elif author.name[-1] == "g":
                author.all_speciality = author_affiliations[6]
            else:
                author.all_speciality = author_affiliations[0]
        except Exception:
            pass


    article_doi = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-doi"]').text.split()[1].strip()

    reference_elements = main_element.find_element(By.TAG_NAME, 'ol').find_elements(By.TAG_NAME, 'li')
    references = [reference_formatter(element.text, False, count) for count, element in enumerate(reference_elements, start=1)]

    article_page_range = [range.strip() for range in main_element.find_element(By.CSS_SELECTOR, 'div[class=article-subinfo]').text.split(':')[-1].split('-')]

    if not "journalofoncology" in start_page:
        # ÇİFT DİLLİLER
        article_title_tr = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-title"]').text.strip()
        article_title_eng = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-title-second"]').text.strip()
        keywords_tr = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-keywords"]').text.strip()
        keywords_tr = [keyword.strip() for keyword in keywords_tr[keywords_tr.index(":")+1:].strip().split(";")]

        keywords_eng = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-keywords"]')[-1].text.strip()
        keywords_eng = [keyword.strip() for keyword in keywords_eng[keywords_eng.index(":")+1:].strip().split(";")]

        abstract_tr = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-abstract"]').text.strip()
        abstract_eng = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-abstract"]')[1].text.strip()

    else:
        article_title_eng = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-title"]').text.strip()
        article_title_tr = None

        keywords_eng = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-keywords"]').text.strip()
        keywords_eng = [keyword.strip() for keyword in keywords_eng[keywords_eng.index(":")+1:].strip().split(";")]
        keywords_tr = None

        abstract_eng = main_element.find_element(By.CSS_SELECTOR, 'div[class="article-abstract"]').text.strip()
        abstract_tr = None

    if "tjrms" in start_page:
        abbreviation = "TJRMS."
    elif "jpmrs" in start_page:
        abbreviation = "J PMR Sci."
    else:
        abbreviation = "J Oncol Sci."
"""
    final_article_data = {
        "journalName": "JOURNAL_NAME",
        "articleType": article_type,
        "articleDOI": article_doi,
        "articleCode": abbreviation,
        "articleYear": 2022,
        "articleVolume": 2,
        "articleIssue": 2,
        "articlePageRange": article_page_range,
        "articleTitle": {"TR": article_title_tr,
                         "ENG": article_title_eng},
        "articleAbstracts": {"TR": abstract_tr,
                             "ENG": abstract_eng},
        "articleKeywords": {"TR": keywords_tr,
                            "ENG": keywords_eng},
        "articleAuthors": [],
        "articleReferences": references}

    pprint.pprint(final_article_data)
"""




