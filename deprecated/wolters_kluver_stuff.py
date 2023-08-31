# Python libraries
import pprint
import random
import time
import os
import re
import json

from fuzzywuzzy import fuzz

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
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")

links = ["https://journals.lww.com/jons/pages/default.aspx", "https://journals.lww.com/tjps/Pages/default.aspx", "https://journals.lww.com/JOMR/pages/default.aspx"]
with (webdriver.Chrome(service=service, options=options) as driver):
    for link in links:
        driver.get(link)
        time.sleep(5)
        current_issue_element = driver.find_element(By.CSS_SELECTOR, 'h3[id^="ctl00"]')
        numbers = [int(number.strip()) for number in re.findall(r'\d+',current_issue_element.text)]
        year = numbers[0]
        recent_volume = numbers[1]
        recent_issue = numbers[2]

        driver.get(link.replace("default", "currenttoc"))
        try:
            time.sleep(1)
            driver.find_element(By.CSS_SELECTOR, 'button[id="onetrust-reject-all-handler"]').click()
        except:
            pass
        article_urls = []
        for item in driver.find_element(By.CSS_SELECTOR, 'div[class="article-list"]').find_elements(By.TAG_NAME, 'h4'):
            article_urls.append(item.find_element(By.TAG_NAME, 'a').get_attribute('href'))
        for item in article_urls:
            try:
                time.sleep(1)
                driver.find_element(By.CSS_SELECTOR, 'button[id="onetrust-reject-all-handler"]').click()
            except:
                pass

            driver.get(item)
            time.sleep(2.5)






    driver.get("https://journals.lww.com/jomr/fulltext/2023/11010/a_retrospective_study_on_variations_of_uncinate.1.aspx")
    try:
        time.sleep(3)
        driver.find_element(By.CSS_SELECTOR, 'button[id="onetrust-reject-all-handler"]').click()
    except:
        pass

    type = driver.find_element(By.CSS_SELECTOR, 'div[class="ejp-r-article-subsection__text"]').text
    title = driver.find_element(By.CSS_SELECTOR, 'h1[class="ejp-article-title"]').text
    #
    authors_element = driver.find_element(By.CSS_SELECTOR, 'section[id="ejp-article-authors"]')
    # Sample names: Koothati, Ramesh Kumar; Yendluru, Mercy Sravanthi; Dirasantchu, Suresh; Muvva, Himapavana; Khandare, Samadhan; Kallumatta, Avinash
    author_names = authors_element.find_element(By.CSS_SELECTOR, 'p[id="P7"]').text.split(';')
    formatted_author_names = [(name_section.split(',')[1].strip() + ' ' + name_section.split(',')[0].strip()).strip() for name_section in author_names]

    driver.find_element(By.CSS_SELECTOR, 'a[id="ejp-article-authors-link"]').click()
    time.sleep(5)
    main_affiliation_element = driver.find_element(By.CSS_SELECTOR, 'div[class="ejp-article-authors-info-holder"]')
    affiliations = list()
    correspondence_name, correspondence_email = None, None
    for affiliation in main_affiliation_element.text.split('\n'):
        if affiliation.startswith("Address for"):
            try:
                correspondence_name = affiliation[affiliation.index(":")+1 : affiliation.index(",")].strip()
            except:
                pass
            try:
                correspondence_email = affiliation.strip().split()[-1]
            except:
                pass
            break
        else:
            affiliations.append(affiliation.strip())


    # construct authors
    author_objects = list()
    for author_name in formatted_author_names:
        author_to_add = Author()
        author_to_add.name = author_name.strip()[:-1] if author_name.strip()[-1].isdigit() else author_name.strip()
        author_to_add.is_correspondence = True if fuzz.ratio(author_to_add.name.lower(),
                                                                          correspondence_name.lower()) > 80 else False
        if len(affiliations) == 1:
            author_to_add.all_speciality = affiliations[0][1:] if affiliations[0][0].isdigit() else affiliations[0]
            author_to_add.name = re.sub(r'\d', '', author_to_add.name)
        else:
            try:
                try:
                    affiliation_code = int(re.search(r'\d',author_to_add.name[-1] ).group(0))
                except:
                    affiliation_code = 0
                for affil in affiliations:
                    if affil[0].isdigit() and int(affil[0]) == affiliation_code:
                        author_to_add.all_speciality = affil[1:]
                if not author_to_add.all_speciality:
                    author_to_add.all_speciality = affiliations[0]
                author_to_add.name = re.sub(r'\d', '', author_to_add.name)
            except Exception as e:
                print(e)
                print("random vurdu")
                author_to_add.all_speciality = random.choice(affiliations)
        if author_to_add.is_correspondence:
            author_to_add.mail = correspondence_email
        author_objects.append(author_to_add)
    pprint.pprint(author_objects, width=150)



    # page range
    bulk_text = driver.find_element(By.CSS_SELECTOR, 'span[id="ej-journal-date-volume-issue-pg"]').text
    page_range = [int(number.strip()) for number in bulk_text[bulk_text.index(":p")+2:bulk_text.index(",")].split('-')]

    #doi
    doi = driver.find_element(By.CSS_SELECTOR, 'div[class="ej-journal-info"]').text.strip().split()[-1]

    abstract = driver.find_element(By.CSS_SELECTOR, 'div[class="ejp-article-text-abstract"]').text.strip()
    driver.execute_script("window.scrollBy(0, 10000)")
    button = driver.find_element(By.CSS_SELECTOR, 'button[class="article-references__button"]')
    driver.execute_script("arguments[0].click();", button)

    time.sleep(3)
    references_text = driver.find_element(By.CSS_SELECTOR, 'section[id="article-references"]')
    references = references_text.find_elements(By.CSS_SELECTOR, 'div[class="article-references__item js-article-reference"]')
    for reference in references:
        print(reference.get_attribute('innerHTML')[:reference.get_attribute('innerHTML').index('<d')].replace("&nbsp;", "").strip())

    keywords = [keyword.get_attribute('data-value').strip() for keyword in driver.find_element(By.XPATH, '//*[@id="ej-article-view"]/div/div').find_elements(By.CSS_SELECTOR, 'span[class="ej-keyword"]')]










