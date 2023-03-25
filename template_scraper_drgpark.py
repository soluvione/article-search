"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
import time
import os
import glob
import re
from pathlib import Path
# Local imports
from classes.author import Author
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.scrape_helpers.drgprk_helper import reference_formatter
from common.services.post_json import post_json
from common.services.send_sms import send_notification
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
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

# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
download_path = os.path.dirname(os.path.abspath(__file__)) + r'\downloads'
options.add_experimental_option('prefs', {"plugins.always_open_pdf_externally": True})
options.add_experimental_option('prefs', {"download.default_directory": download_path})
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Metadata about the journal
# Scrape types has 2 options, either unique (A_UNQ) or Dergipark (A_DRG). PDF scrape types can vary more than that.
journal_name = f""
scrape_type = "A_DRG"
pdf_scrape_type = "A_UNQ"
start_page_url = f""
font_sizes_ntypes = {"Abstract": ["ftype", "size"],
                     "Article Type": ["ftype", "size"],
                     "Authors": ["ftype", "size"],
                     "Author Info": ["ftype", "size"],
                     "Header": ["ftype", "size"],
                     "Keywords": ["ftype", "size"],
                     "References": ["ftype", "size"]}
"""
SPECIAL NOTES REGARDING THE JOURNAL (IF APPLICABLE)

"""

# GLOBAL VARS
# For a given journal issue, represents how many journal articles have been scraped successfully.
num_successfully_scraped = 0
# Either contains Article URLs or PDF links of each article element
article_url_list = []
article_download_element_list = []

# GET TO THE PAGE
if requests.head(start_page_url).status_code != 200:
    send_notification(DownServerError(f"Servers of the journal {journal_name} are down."))
    raise DownServerError(f"Servers of the journal {journal_name} are down.")
try:
    driver.get(start_page_url)
except WebDriverException:
    send_notification(ScrapePathError(f"Could not reach the webpage of {journal_name}."))
    raise ScrapePathError(f"Could not reach the webpage of {journal_name}.")

# GET THE DATA ABOUT THE LATEST ISSUE/VOLUME
try:
    latest_publication_element = driver.find_element(By.CSS_SELECTOR, '.kt-widget-18__item')
except NoSuchElementException:
    send_notification(ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down."))
    raise ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down.")

temp_txt = latest_publication_element.text
recent_volume = int(temp_txt[temp_txt.index(":") + 1:temp_txt.index("Sayı")].strip())
recent_issue = int(temp_txt.split()[-1])

# START DOWNLOADS IF ISSUE IS NOT SCANNED
if not is_issue_scanned(vol_num=recent_volume, issue_num=recent_issue, path_=__file__):
    # GET TO THE ISSUE PAGE
    try:
        driver.get(latest_publication_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
    except NoSuchElementException:
        send_notification(ScrapePathError(f"Could not retrieve element of the webpage of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve element of the webpage of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")
    time.sleep(1)

    # SCRAPE ARTICLE ELEMENTS AS SELENIUM ELEMENTS
    try:
        article_elements = driver.find_elements(By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')
    except Exception:
        send_notification(ScrapePathError(f"Could not retrieve article urls of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve article urls of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")

    # SCRAPE ARTICLE PAGE URL OR DOWNLOAD LINK OR DOWNLOAD ITEM LOCATORS FROM EACH ELEMENT
    article_num = 0
    for article in article_elements:
        try:
            article_url = article.find_element(By.CSS_SELECTOR, '.card-title.article-title').get_attribute('href')
            article_url_list.append(article_url)
        except Exception:
            # Does not end the iteration but only sends an SMS.
            send_notification(
                ScrapePathError(f"Article url does not exist for the {journal_name, recent_volume, recent_issue}"
                                f", article {article_num}."))
        article_num += 1

    # GET TO THE ARTICLE PAGE AND TRY TO DOWNLOAD AND PARSE THE ARTICLE PDFs
    article_num = 0
    for article_url in article_url_list:
        article_num += 1
        if article_num > 1:
            driver.execute_script("window.history.go(-1)")
            WebDriverWait(driver, timeout=3).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')))
        parse_nsend_successful = True
        if not is_article_scanned_url(url=article_url, path_=__file__):
            try:
                # ARTICLE VARIABLES SCRAPED FROM DERGIPARK PAGE
                is_scraped_online = True
                article_type = None
                article_title_tr = None
                article_title_eng = None
                authors = []
                references = []
                keywords_tr = []
                keywords_eng = []
                abstract_tr = None
                abstract_eng = None
                doi = None
                article_lang_num = None
                # GET TO ARTICLE PAGE AND GET ELEMENTS IF POSSIBLE FROM THE UNIQUE ARTICLE PAGE
                driver.get(article_url)
                lang_navbar = driver.find_element(By.CSS_SELECTOR,
                                                  'ul.nav.nav-tabs.nav-tabs-line.nav-tabs-line-dergipark.nav-tabs-line-3x.nav-tabs-line-right.nav-tabs-bold')
                language_tabs = lang_navbar.find_elements(By.CSS_SELECTOR, '.nav-item')
                article_lang_num = len(language_tabs)
                article_type = identify_article_type(
                    driver.find_element(By.CSS_SELECTOR, 'div.kt-portlet__head-title').text)

                if article_lang_num == 1:
                    if "Türkçe" in driver.find_element(By.CSS_SELECTOR, 'table.record_properties.table').find_element(
                            By.TAG_NAME, 'tr').text:
                        article_lang = "TR"
                    else:
                        article_lang = "ENG"
                    article_title_element = driver.find_element(By.CSS_SELECTOR, 'h3.article-title')
                    keywords_element = driver.find_element(By.CSS_SELECTOR, 'div.article-keywords.data-section')
                    abstract_element = driver.find_element(By.CSS_SELECTOR, 'div.article-abstract.data-section')
                    reference_list_elements = driver.find_element(
                        By.CSS_SELECTOR, 'div.article-citations.data-section').find_elements(By.TAG_NAME, 'li')
                    for reference_element in reference_list_elements:
                        references.append(reference_element.text)

                    if article_lang == "TR":
                        article_title_tr = article_title_element.text
                        abstract_tr = abstract_element.find_element(By.TAG_NAME, 'p').text
                        for keyword in keywords_element.find_element(By.TAG_NAME, 'p').text.split(','):
                            keywords_tr.append(keyword.strip())
                    else:
                        article_title_eng = article_title_element.text
                        abstract_eng = abstract_element.find_element(By.TAG_NAME, 'p').text
                        for keyword in keywords_element.find_element(By.TAG_NAME, 'p').text.split(','):
                            keywords_eng.append(keyword.strip())
                elif article_lang_num == 2:
                    # GO TO TURKISH TAB
                    language_tabs[0].click()
                    time.sleep(0.7)
                    tr_article_element = driver.find_element(By.ID, 'article_tr')
                    article_title_tr = tr_article_element.find_element(By.CSS_SELECTOR, 'h3.article-title').text
                    abstract_tr = tr_article_element.find_element(By.CSS_SELECTOR,
                                                                  'div.article-abstract.data-section') \
                        .find_element(By.TAG_NAME, 'p').text
                    keywords_element = tr_article_element.find_element(By.CSS_SELECTOR,
                                                                       'div.article-keywords.data-section')

                    for keyword in keywords_element.find_element(By.TAG_NAME, 'p').text.split(','):
                        keywords_tr.append(keyword.strip())
                    keywords_tr[-1] = re.sub(r'\.', '', keywords_tr[-1])

                    # GO TO ENGLISH TAB
                    language_tabs[1].click()
                    time.sleep(0.7)
                    eng_article_element = driver.find_element(By.ID, 'article_en')
                    article_title_eng = eng_article_element.find_element(By.CSS_SELECTOR, 'h3.article-title').text
                    abstract_eng = eng_article_element.find_element(By.CSS_SELECTOR,
                                                                    'div.article-abstract.data-section') \
                        .find_element(By.TAG_NAME, 'p').text
                    keywords_element = eng_article_element.find_element(By.CSS_SELECTOR,
                                                                        'div.article-keywords.data-section')

                    for keyword in keywords_element.find_element(By.TAG_NAME, 'p').text.split(','):
                        keywords_eng.append(keyword.strip())
                    keywords_eng[-1] = re.sub(r'\.', '', keywords_eng[-1])

                    reference_list_elements = eng_article_element.find_element(
                        By.CSS_SELECTOR, 'div.article-citations.data-section').find_elements(By.TAG_NAME, 'li')
                    for reference_element in reference_list_elements:
                        references.append(reference_formatter(reference_element.text))

                author_elements = driver.find_elements(By.CSS_SELECTOR, "p[id*='author']")
                for author_element in author_elements:
                    authors.append(author_converter(author_element.get_attribute('innerHTML')))

                try:
                    doi = driver.find_element(By.CSS_SELECTOR, 'a.doi-link').text
                except NoSuchElementException:
                    pass

            except Exception:
                send_notification(GeneralError(
                    f"Scraping journal elements of Dergipark journal"
                    f" {journal_name, recent_volume, recent_issue}"
                    f" with article num {article_num} was not successful."))
                is_scraped_online = False

            try:
                # PDF LINK THAT WHEN DRIVER GETS THERE THE DOWNLOAD STARTS
                driver.get(driver.find_element
                           (By.CSS_SELECTOR, 'a.btn.btn-sm.float-left.article-tool.pdf.d-flex.align-items-center')
                           .get_attribute('href'))
            except Exception:
                send_notification(DownloadError(
                    f"Downloading the article with num of {article_num} of the journal"
                    f" {journal_name, recent_volume, recent_issue} was "
                    f"not successful."))
                clear_directory(download_path)
                continue

            # CHECK IF THE DOWNLOAD HAS BEEN FINISHED
            if not check_download_finish(download_path):
                send_notification(DownloadError(f"Download was not finished in time, "
                                                f"{journal_name, recent_volume, recent_issue},"
                                                f" article num {article_num}."))
                if clear_directory(download_path):
                    continue
                else:
                    send_notification(GeneralError(f"Downloaded file could not deleted, "
                                                   f"{journal_name, recent_volume, recent_issue},"
                                                   f" article num {article_num}."))
                    continue

            # PARSE THE SCANNED PDF
            path_to_pdf = max(glob.iglob(os.path.dirname(os.path.abspath(__file__)) + r'\*'), key=os.path.getmtime)
            parsed_text = ""
            try:
                parsed_text = parser.get_text_with_specs(path_=path_to_pdf, num_pages=1, font1_size=12.00)
            except Exception:
                # Does not end the iteration but only sends an SMS.
                send_notification(
                    ParseError(f"Article could not be parsed, journal: {journal_name, recent_volume, recent_issue}"
                               f", article: {article_num}."))
                clear_directory(download_path)
                continue

            # HARVEST DATA FROM PARSED TEXT
            article_data = {"Article Type": "",
                            "Article Title": {"TR": "", "ENG": ""},
                            "Article Abstracts": {"TR": "", "ENG": ""},
                            "Article Keywords": {"TR": [], "ENG": []},
                            "Article DOI": "",
                            "Article Headline": "",
                            "Article Authors": [],
                            "Article References": []}
            if article_type:
                article_data["Article Type"] = article_type

            if article_title_tr:
                article_data["Article Title"]["TR"] = article_title_tr
            if article_title_eng:
                article_data["Article Title"]["ENG"] = article_title_eng

            if abstract_tr or abstract_eng:
                if abstract_eng:
                    article_data["Article Abstracts"]["ENG"] = abstract_eng
                if abstract_tr:
                    article_data["Article Abstracts"]["TR"] = abstract_tr

            if keywords_tr or keywords_eng:
                if keywords_tr:
                    article_data["Article Keywords"]["TR"] = keywords_tr
                if keywords_eng:
                    article_data["Article Keywords"]["ENG"] = keywords_eng

            if doi:
                article_data["Article DOI"] = doi

            # Get Headliner

            if authors:
                article_data["Article Authors"] = authors
            # Get Author Mail and Comm Details

            if references:
                article_data["Article References"] = references

            # DELETE DOWNLOADED PDF
            clear_directory(download_path)

            # POST THE DATA TO THE BACKEND
            try:
                post_json(article_data)
            except Exception:
                parse_nsend_successful = False
                send_notification(DataPostError(f"Article data could not be posted to the backend, journal: "
                                                f"{journal_name, recent_volume, recent_issue}, article: {article_num}"))

            # UPDATE THE SCANNED ARTICLES LIST IF PARSED
            if parse_nsend_successful:
                update_scanned_articles(url=article_url, is_doi=False, path_=__file__)
                num_successfully_scraped += 1

            if article_num == 1:
                driver.execute_script("window.history.go(-1)")
                WebDriverWait(driver, timeout=3).until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')))

if ((num_successfully_scraped / len(article_url_list)) * 100) > 80:
    update_scanned_issues(vol_num=recent_volume, issue_num=recent_issue, path_=__file__)
    send_notification(
        f"Scraping and harvesting data was successful, Journal: {journal_name, recent_volume, recent_issue}")
else:
    send_notification(GeneralError(f"Majority of the journals were not scraped {journal_name}."))

driver.close()
clear_directory(download_path)
