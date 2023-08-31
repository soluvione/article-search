"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
import time
import os
import glob
from pathlib import Path
# Local imports
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
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
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# Metadata about the journal
# Scrape types has 2 options, either unique (A_UNQ) or Dergipark (A_DRG). PDF scrape types can vary more than that.
journal_name = f""
scrape_type = "A_UNQ"
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
    latest_publication_element = driver.find_element(By.CSS_SELECTOR, '')
except NoSuchElementException:
    send_notification(ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down."))
    raise ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down.")

temp_txt = latest_publication_element.text
recent_volume = 0
recent_issue = 0

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
        article_elements = driver.find_elements(By.CSS_SELECTOR, '')
    except Exception:
        send_notification(ScrapePathError(f"Could not retrieve article urls of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve article urls of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")

    # SCRAPE ARTICLE PAGE URL OR DOWNLOAD LINK OR DOWNLOAD ITEM LOCATORS FROM EACH ELEMENT
    article_num = 0
    for article in article_elements:
        try:
            article_url = article.find_element(By.CSS_SELECTOR, '').get_attribute('href')
            article_url_list.append(article_url)
            # OR
            download_element = article.find_element(By.CSS_SELECTOR, '')
            article_download_element_list.append(download_element)
        except Exception:
            # Does not end the iteration but only sends an SMS.
            send_notification(
                ScrapePathError(f"Article url does not exist for the {journal_name, recent_volume, recent_issue}"
                                f", article {article_num}."))
        article_num += 1

    # TRY TO DOWNLOAD AND PARSE THE ARTICLE PDFs
    article_num = 0
    for article_url in article_url_list:
        article_num += 1
        if article_num > 1:
            driver.execute_script("window.history.go(-1)")
            WebDriverWait(driver, timeout=3).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '')))
        parse_nsend_successful = True
        if not is_article_scanned_url(url=article_url, path_=__file__):
            try:
                # GET TO THE DOWNLOAD LINK OR CLICK THE DOWNLOAD BUTTON
                driver.get(article_url)
                # 1 PDF LINK THAT WHEN DRIVER GETS THERE THE DOWNLOAD STARTS
                driver.get(driver.find_element(By.CSS_SELECTOR, '').get_attribute('href'))
                # 2 BUTTON
                download_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located(By.CSS_SELECTOR, ''))
                download_button.click()
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
                parsed_text = parser.get_text_with_specs(path_=path_to_pdf, num_pages=1, font_type=12.00)
            except Exception:
                # Does not end the iteration but only sends an SMS.
                send_notification(
                    ParseError(f"Article could not be parsed, journal: {journal_name, recent_volume, recent_issue}"
                               f", article: {article_num}."))
                clear_directory(download_path)
                continue

            # HARVEST DATA FROM PARSED TEXT
            article_data = {"Article Title": "",
                            "Article Type": "",
                            "Article Headline": "",
                            "Article Authors": [],
                            "Article DOI": "",
                            "Article Abstracts": {"TR": "", "ENG": ""},
                            "Article Keywords": {"TR": [], "ENG": []},
                            "Article References": []}
            author_num = 0

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

if ((num_successfully_scraped / len(article_url_list)) * 100) > 80:
    update_scanned_issues(vol_num=recent_volume, issue_num=recent_issue, path_=__file__)
    send_notification(f"Scraping and harvesting data was successful, Journal: {journal_name, recent_volume, recent_issue}")
else:
    send_notification(GeneralError(f"Majority of the journals were not scraped {journal_name}."))

driver.close()
clear_directory(download_path)
