# Python libraries
import pprint
import time
import os
import re
import json

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


with webdriver.Chrome(service=service, options=options) as driver:
    start_page = "https://parkinson.org.tr/tur"
    if not "parkinson" in start_page:
        driver.get(start_page + "/current-issue")
    else:
        driver.get(start_page + "/son-sayi")


    current_issue_element = driver.find_element(By.CSS_SELECTOR, 'div[class="page-header"]')
    numbers = re.findall('[0-9]+', current_issue_element.text)
    year = int(numbers[0])
    recent_volume = int(numbers[1])
    recent_issue = int(numbers[2])

    main_articles_element = driver.find_element(By.CSS_SELECTOR, 'div[class="span9"]') if not "jsurg" in start_page else driver.find_element(By.CSS_SELECTOR, 'div[class="span12"]')
    article_elements = main_articles_element.find_elements(By.TAG_NAME, 'h3')
    urls = list()
    for article_element in article_elements:
        urls.append(article_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))

    for url in urls:
        start_page_url = url
        try:
            if not "parkinson" in start_page_url:
                full_text_page = start_page_url.replace("abstract", "full-text")
            else:
                 if not start_page_url.endswith("tur"):
                     full_text_page = start_page_url.replace("ozet", "tam-metin")
                 else:
                     full_text_page = start_page_url
            driver.get(full_text_page)

            article_title = driver.find_element(By.CLASS_NAME, 'page-header').text.strip()

            meta_element = driver.find_element(By.ID, 'article-meta')

            # Authors
            author_names = meta_element.find_elements(By.TAG_NAME, 'p')[0].text.split(',')
            try:
                author_affiliations = meta_element.find_elements(By.TAG_NAME, 'p')[1].text.split('\n')
            except:
                continue

            author_objects = list()
            for author_name in author_names:
                if len(author_affiliations) == 1:
                if len(author_affiliations) == 1:
                    author_objects.append(Author(name=author_name, all_speciality=author_affiliations[0]))
                else:
                    author = Author()
                    author.name = author_name[:-1]
                    try:
                        author_code = int(author_name[-1])
                        author.all_speciality = author_affiliations[author_code - 1][1:]
                    except Exception:
                        pass
                    author_objects.append(author)

                aff = meta_element.find_elements(By.TAG_NAME, 'p')[1].text
            try:
                key = meta_element.find_elements(By.TAG_NAME, 'p')[2].text
            except:
                try:
                    key = driver.find_element(By.ID, 'article-abstract').find_elements(By.TAG_NAME, 'p')[-1].text
                except:
                    continue

            try:
                # Download Link
                download_link = url.replace("text", "pdf")
            except Exception:
                download_link = None


            try:
                abstract = driver.find_element(By.ID, 'article-abstract').text.strip()
            except:
                abstract = driver.find_element(By.ID, 'article_abstract').text.strip()
            time.sleep(2)
            try:
                right_bar = driver.find_element(By.CSS_SELECTOR, 'aside[class="well well-small affix-top"]')
            except:
                try:
                    right_bar = driver.find_element(By.CSS_SELECTOR, 'div[class="panel affix-top"]')
                except:
                    raise GeneralError
            article_page_range_text = right_bar.find_elements(By.TAG_NAME, 'p')[1].text
            article_page_range = [int(number) for number in re.findall('\d+', article_page_range_text)]
            doi = right_bar.find_elements(By.TAG_NAME, 'p')[2].text
            doi = doi[doi.index(":")+ 1:].strip()
            a_type = right_bar.find_elements(By.TAG_NAME, 'p')[3].text
            a_type = a_type[a_type.index(":")+1:].strip()

            references = [reference_formatter(reference, True, count)
                          for count, reference
                          in enumerate(driver.find_element(By.ID, 'article-references').text.split('\n'), start=1)
                          if reference_formatter(reference, True, count)]

            full_text = start_page_url.replace("abstract", "full-text")
            download_link = start_page_url.replace("abstract", "full-text-pdf")

            # Abbreviation
            if "parkinson" in start_page_url:
                abbreviation = "Parkinson Hast Harek Boz Derg."
            elif "journalofsportsmedicine" in start_page_url:
                abbreviation = "TurkJ Sports Med."
            elif "turkjsurg" in start_page_url:
                abbreviation = "Turk J Surg"
            else:
                abbreviation = "Arch Rheumatol"

            only_english = "turkjsurg, archivesofrheumatology"
            base_turkish = "parkinson"
            #bu ilk bulunanlar dergi diline göre burada dağıtılacak.
            if not "parkinson" in start_page_url:
                article_title_eng = article_title
                keywords_eng = [keyword.strip() for keyword in key[key.index(":")+1 :].split(',')]
                abstract_eng = abstract
            else:
                article_title_tr = article_title
                keywords_tr = [keyword.strip() for keyword in key[key.index(":")+1 :].split(',')]
                abstract_tr = abstract


            if not "turkjsurg" in start_page_url and not "archivesofrheumatology" in start_page_url:
                # then there are turkish parts to be scraped
                if "parkinson" in start_page_url:
                    new_url = full_text_page.replace("tam-metin", "ozet")[:-4]
                    driver.get(new_url)
                    time.sleep(0.5)
                    meta_element = driver.find_element(By.ID, 'article-meta')
                    keywords_eng = meta_element.find_elements(By.TAG_NAME, 'p')[2].text.strip()
                    keywords_eng = [keyword.strip() for keyword in keywords_eng[keywords_eng.index(":")+1 :].split(',')]
                    article_title_eng = driver.find_element(By.CLASS_NAME, 'page-header').text.strip()
                    abstract_eng = driver.find_element(By.XPATH, '//*[@id="article_abstract"]').text.strip()

                else:
                    new_url = full_text_page.replace("full-text", "abstract").replace("eng", "tur")
                    driver.get(new_url)
                    time.sleep(0.5)
                    meta_element = driver.find_element(By.ID, 'article-meta')
                    abstract_tr = driver.find_element(By.ID, 'article_abstract').text.strip()
                    keywords_tr = meta_element.find_elements(By.TAG_NAME, 'p')[2].text.strip()
                    keywords_tr = [keyword.strip() for keyword in keywords_tr[keywords_tr.index(":")+1:].split(",")]
                    article_title_tr = driver.find_element(By.CLASS_NAME, 'page-header').text.strip()
            else:
                article_title_tr = None
                keywords_tr = None
                abstract_tr = None

            final_article_data = {
                "journalName": "dergi",
                "articleType": a_type,
                "articleDOI": doi,
                "articleCode": abbreviation,
                "articleYear": 2,
                "articleVolume": 1,
                "articleIssue": 2,
                "articlePageRange": article_page_range,
                "articleTitle": {"TR": article_title_tr,
                                 "ENG": article_title_eng},
                "articleAbstracts": {"TR": abstract_tr,
                                     "ENG": abstract_eng},
                "articleKeywords": {"TR": keywords_tr,
                                    "ENG": keywords_eng},
                "articleAuthors": Author.author_to_dict(author_objects),
                "articleReferences": references if references else []}
            pprint.pprint(final_article_data)
            time.sleep(20)
        except:
            continue
