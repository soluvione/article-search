"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
from datetime import datetime
import time
import os
import glob
import re
import json
from pathlib import Path
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
from common.helpers.methods.pdf_cropper import crop_pages
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
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Metadata about the journal
# Scrape types has 2 options, either unique (A_UNQ) or Dergipark (A_DRG). PDF scrape types can vary more than that.
journal_name = f""
scrape_type = f"https://dergipark.org.tr/tr/pub/jgehes"
pdf_scrape_type = "A_UNQ"
start_page_url = f""
font_sizes_ntypes = {"Abstract": ["ftype", "size"],
                     "Article Type": ["ftype", "size"],
                     "Authors": ["ftype", "size"],
                     "Author Info": ["ftype", "size"],
                     "Code": ["ftype", "size"],  # Article headline code. Eg: Eur Oral Res 2023; 57(1): 1-9
                     "Keywords": ["ftype", "size"],
                     "References": ["ftype", "size"]}
"""
SPECIAL NOTES REGARDING THE JOURNAL (IF APPLICABLE)

"""

# GLOBAL VARS
# For a given journal issue, represents how many journal articles have been scraped successfully.
num_successfully_scraped = 0
pdf_to_download_available = False
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

    # SCRAPE YEAR INFORMATION OF THE ISSUE
    try:
        issue_year = driver.find_element(By.CSS_SELECTOR, 'span.kt-widget-12__desc').text.split()[-1]
    except NoSuchElementException:
        # If for any reason try suite fails, the default year is set to the current year
        # This method will work fine for 99% of the times, will give correct year data
        issue_year = datetime.now().year

    # SCRAPE ARTICLE ELEMENTS AS SELENIUM ELEMENTS
    try:
        article_elements = driver.find_elements(By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')
    except Exception:
        send_notification(ScrapePathError(f"Could not retrieve article urls of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve article urls of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")

    # SCRAPE ARTICLE PAGE URL FROM EACH ELEMENT
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
                url = article_url
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
                article_page_range = [0, 1]
                article_lang_num = None
                article_vol = recent_volume
                article_issue = recent_issue
                article_year = issue_year
                article_code = 000000000000000000000  # Enter the code algorithms specific to the article

                # GET TO ARTICLE PAGE AND GET ELEMENTS IF POSSIBLE FROM THE UNIQUE ARTICLE PAGE
                driver.get(article_url)

                article_type = identify_article_type(
                    driver.find_element(By.CSS_SELECTOR, 'div.kt-portlet__head-title').text, len(driver.find_elements(
                        By.CSS_SELECTOR, 'div.article-citations.data-section')))
                if article_type == "Diğer" or article_type == "Editoryal":
                    continue

                article_subtitle_elements = driver.find_elements(By.CSS_SELECTOR, 'span.article-subtitle')
                for element in article_subtitle_elements:
                    if element.text:
                        article_page_range = element.text.split(',')[-2].strip().split('-')
                        article_page_range = [int(page_num) for page_num in article_page_range]

                lang_navbar = driver.find_element(By.CSS_SELECTOR,
                                                  'ul.nav.nav-tabs.nav-tabs-line.nav-tabs-line-dergipark.nav-tabs-line-3x.nav-tabs-line-right.nav-tabs-bold')
                language_tabs = lang_navbar.find_elements(By.CSS_SELECTOR, '.nav-item')
                article_lang_num = len(language_tabs)

                if article_lang_num == 1:
                    if "Türkçe" in driver.find_element(By.CSS_SELECTOR, 'table.record_properties.table').find_element(
                            By.TAG_NAME, 'tr').text:
                        article_lang = "TR"
                    else:
                        article_lang = "ENG"

                    article_title_elements = driver.find_elements(By.CSS_SELECTOR, 'h3.article-title')
                    keywords_elements = driver.find_elements(By.CSS_SELECTOR, 'div.article-keywords.data-section')
                    abstract_elements = driver.find_elements(By.CSS_SELECTOR, 'div.article-abstract.data-section')
                    if scrape_type == "A_DRG & R":
                        button = driver.find_element(By.XPATH, '//*[@id="show-reference"]')
                        button.click()
                        time.sleep(0.25)
                        reference_list_elements = driver.find_elements(
                            By.CSS_SELECTOR, 'div.article-citations.data-section')
                        for reference_element in reference_list_elements:
                            if reference_element.find_elements(By.TAG_NAME, 'li')[0].text:
                                ref_count = 1
                                for element in reference_element.find_elements(By.TAG_NAME, 'li'):
                                    if ref_count == 1:
                                        references.append(reference_formatter(element.get_attribute('innerText'), is_first=True, count=ref_count))
                                    else:
                                        references.append(reference_formatter(element.get_attribute('innerText'), is_first=False, count=ref_count))
                                    ref_count += 1
                    if article_lang == "TR":
                        for element in article_title_elements:
                            if element.text:
                                article_title_tr = element.text
                        for element in abstract_elements:
                            if element.text:
                                abstract_tr = abstract_formatter(element.find_element(By.TAG_NAME, 'p').text, "tr")
                        for element in keywords_elements:
                            if element.text:
                                for keyword in element.find_element(By.TAG_NAME, 'p').text.split(','):
                                    if keyword.strip() and keyword.strip() not in keywords_tr:
                                        keywords_tr.append(keyword.strip())
                    else:
                        for element in article_title_elements:
                            if element.text:
                                article_title_eng = element.text
                        for element in abstract_elements:
                            if element.text:
                                abstract_eng = abstract_formatter(element.find_element(By.TAG_NAME, 'p').text, "eng")
                        for element in keywords_elements:
                            if element.text:
                                for keyword in element.find_element(By.TAG_NAME, 'p').text.split(','):
                                    if keyword.strip() and keyword.strip() not in keywords_eng:
                                        keywords_eng.append(keyword.strip())

                elif article_lang_num == 2:
                    # GO TO THE TURKISH TAB
                    language_tabs[0].click()
                    time.sleep(0.7)
                    tr_article_element = driver.find_element(By.ID, 'article_tr')
                    article_title_tr = tr_article_element.find_element(By.CSS_SELECTOR, '.article-title').get_attribute(
                        'innerText').strip()
                    abstract_tr = abstract_formatter(tr_article_element.find_element(By.CSS_SELECTOR,
                                                                  'div.article-abstract.data-section') \
                        .find_element(By.TAG_NAME, 'p').get_attribute('innerText'), "tr")

                    try:
                        keywords_element = tr_article_element.find_element(By.CSS_SELECTOR,
                                                                           'div.article-keywords.data-section')

                        for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute(
                                'innerText').strip().split(','):
                            if keyword.strip() and keyword.strip() not in keywords_tr:
                                keywords_tr.append(keyword.strip())
                        keywords_tr[-1] = re.sub(r'\.', '', keywords_tr[-1])
                    except:
                        send_notification(ParseError(
                            f"Could not scrape keywords of journal {journal_name} with article num {article_num}."))
                        # raise ParseError(f"Could not scrape keywords of journal {journal_name} with article num {article_num}.")
                        pass
                    # GO TO THE ENGLISH TAB
                    language_tabs[1].click()
                    time.sleep(0.7)
                    eng_article_element = driver.find_element(By.ID, 'article_en')
                    article_title_eng = eng_article_element.find_element(By.CSS_SELECTOR, 'h3.article-title').get_attribute('innerText').strip()
                    abstract_eng_element = \
                        eng_article_element.find_element(By.CSS_SELECTOR,
                                                                    'div.article-abstract.data-section') \
                        .find_elements(By.TAG_NAME, 'p')
                    for part in abstract_eng_element:
                        if part.get_attribute('innerText'):
                            abstract_eng = abstract_formatter(part.get_attribute('innerText'), "eng")
                    keywords_element = eng_article_element.find_element(By.CSS_SELECTOR,
                                                                        'div.article-keywords.data-section')

                    for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute('innerText').strip().split(','):
                        if keyword.strip():
                            keywords_eng.append(keyword.strip())

                    keywords_eng[-1] = re.sub(r'\.', '', keywords_eng[-1])
                    if scrape_type == "A_DRG & R":
                        button = driver.find_element(By.XPATH, '//*[@id="show-reference"]')
                        button.click()
                        time.sleep(0.25)
                        reference_list_elements = eng_article_element.find_element(
                            By.CSS_SELECTOR, 'div.article-citations.data-section').find_elements(By.TAG_NAME, 'li')
                        ref_count = 1
                        for reference_element in reference_list_elements:
                            ref_text = reference_element.get_attribute('innerText')
                            if ref_count == 1:
                                references.append(reference_formatter(ref_text, is_first=True,
                                                                          count=ref_count))
                            else:
                                references.append(reference_formatter(ref_text, is_first=False,
                                                                            count=ref_count))
                            ref_count += 1

                author_elements = driver.find_elements(By.CSS_SELECTOR, "p[id*='author']")
                for author_element in author_elements:
                    authors.append(author_converter(author_element.get_attribute('innerText'), author_element.get_attribute('innerHTML')))
                try:
                    doi = driver.find_element(By.CSS_SELECTOR, 'a.doi-link').get_attribute('innerText')
                    doi = doi[doi.index("org/")+4:]
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
                pdf_to_download_available = True
            except Exception:
                pass

            if pdf_to_download_available:
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
                format_file_name(download_path, journal_name+' '+str(recent_volume)+str(recent_issue)+str(article_num))
                # HARVEST DATA FROM PARSED TEXT
                article_data = {"Journal Name": f"{journal_name}",
                                "Article Type": "",
                                "Article DOI": 0,
                                "Article Code": "",
                                "Article Year": issue_year,
                                "Article Volume": recent_volume,
                                "Article Issue": recent_issue,
                                "Article Page Range": article_page_range,
                                "Article Title": {"TR": "", "ENG": ""},
                                "Article Abstracts": {"TR": "", "ENG": ""},
                                "Article Keywords": {"TR": [], "ENG": []},
                                "Article Authors": [],
                                "Article References": []}
                if article_type:
                    article_data["Article Type"] = article_type
                if doi:
                    article_data["Article DOI"] = doi
                if article_code:
                    article_data["Article Code"] = article_code
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
                if authors:
                    article_data["Article Authors"] = Author.author_to_json(authors)
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
