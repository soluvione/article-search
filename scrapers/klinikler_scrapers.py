"""
This is the template scraper that will be used to multiply.
"""

# Python libraries
import time
import os
from datetime import datetime
import json
import glob
import json
import pprint
# Local imports
from classes.author import Author
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.klinikler_helper import format_bulk_data, get_article_titles, \
    pair_authors, get_page_range
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter, get_correspondance_name
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
from common.helpers.methods.data_to_atifdizini import get_to_artc_page, paste_data
from common.services.post_json import post_json
from common.services.azure.azure_helper import AzureHelper
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_sms import send_notification, send_example_log
import common.helpers.methods.others
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
with_adobe = False
with_azure = False
login = False

def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "klinikler_manual", parent_type,
                                  file_reference, "downloads")
    return downloads_path


def get_recently_downloaded_file_name(download_path):
    """
    :param download_path: PATH of the download folder
    :return: Returns the name of the most recently downloaded file
    """
    list_of_files = glob.glob(download_path + '/*')
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


def update_authors_with_correspondence(paired_authors, correspondence_name, correspondence_mail):
    """

    :param paired_authors:
    :param correspondence_name:
    :param correspondence_mail:
    :return:
    """
    for author in paired_authors:
        if common.helpers.methods.others.similarity(author.name, correspondence_name) > 80:
            author.is_correspondence = True
            author.mail = correspondence_mail
    return paired_authors


def klinikler_no_ref_scraper(journal_name, start_page_url, parent_type, file_reference, pdf_scrape_type="A_KLNK_R"):
    i = 1
    while i < 3:
        start_page_url = "https://www.turkiyeklinikleri.com/journal/anesteziyoloji-reanimasyon-dergisi/14/issue/2023/21/1-0//tr-index.html"
        # Webdriver options
        # Eager option shortens the load time. Driver also always downloads the pdfs and does not display them
        options = Options()
        options.page_load_strategy = 'eager'
        # download_path = get_downloads_path(parent_type, file_reference)
        download_path = "/home/emin/Desktop/tk_downloads"
        prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
        options.add_experimental_option('prefs', prefs)
        options.add_argument("--disable-notifications")
        options.add_argument("--headless")  # This line enables headless mode
        service = ChromeService(executable_path=ChromeDriverManager().install())
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(start_page_url)
            # time.sleep(1.25)
            # volume_items = driver.find_element(By.ID, 'volumeList')
            # latest_issue = volume_items.find_elements(By.CLASS_NAME, 'issue')[0]
            # issue_no = latest_issue.find_element(By.CLASS_NAME, 'issueNo').text
            if 2 < 4:  # check scan
                # issue_link = latest_issue.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                article_urls = []
                article_list = driver.find_element(By.ID, 'articleList')
                article_elements = article_list.find_elements(By.ID, 'article')
                for item in article_elements:
                    if not item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').text.strip() == "ÖN SÖZ":
                        article_urls.append(
                            item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').get_attribute('href'))
                if login:
                    login_button_xpath = driver.find_element(By.XPATH, '/html/body/div/section/div[2]/div[1]/div/a[1]')
                    login_button_xpath.click()
                    time.sleep(3)
                    username_xpath = driver.find_element(By.XPATH, '//*[@id="tpl_login_username"]')
                    username_xpath.send_keys('eminens06@gmail.com')
                    time.sleep(1)
                    password_xpath = driver.find_element(By.XPATH, '//*[@id="tpl_login_password"]')
                    password_xpath.send_keys('h9quxA0vCx')
                    time.sleep(1)
                    confirm_button_xpath = driver.find_element(By.XPATH, '//*[@id="tpl_login_submit"]')
                    confirm_button_xpath.click()
                    time.sleep(7)
                # driver.get(issue_link)
                # time.sleep(7)

                for url in article_urls:
                    driver.get(url)

                    # Titles in Turkish and English
                    article_element = driver.find_element(By.ID, 'article')
                    turkish_title, english_title = get_article_titles(article_element)

                    # Article Language
                    article_language = article_element.find_elements(By.CLASS_NAME, 'altBilgi')[1].text.split(':')[1].strip().lower()

                    # Article Type
                    try:
                        article_type = article_element.find_element(By.CLASS_NAME, 'header').text.strip()
                        article_type = ''.join([char for char in article_type if char.isalpha() or char.isspace()])
                    except Exception:
                        article_type = None
                    print(article_type)

                    # Author Names and Specialities
                    authors_element = article_element.find_element(By.CLASS_NAME, 'author')
                    author_names_list = [author.strip() for author in
                                         authors_element.text[: authors_element.text.find('\n')].split(',')]
                    author_specialities = [speciality for speciality in authors_element.text.split('\n')[1:]]
                    paired_authors = pair_authors(author_names_list, author_specialities)

                    # Abstract and Keywords (The order of the languages is not fixed)
                    if article_language == "tr":
                        abstract_keywords_tr = article_element.find_element(By.CLASS_NAME, 'summaryMain').text.strip()
                        abstract_tr, keywords_tr = format_bulk_data(abstract_keywords_tr, language="tr")
                        try:
                            abstract_keywords_eng = article_element.find_element(By.CLASS_NAME, 'summarySub').text.strip()
                            abstract_eng, keywords_eng = format_bulk_data(abstract_keywords_eng, language="eng")
                        except Exception:
                            pass
                    else:
                        abstract_keywords_eng = article_element.find_element(By.CLASS_NAME, 'summaryMain').text.strip()
                        abstract_eng, keywords_eng = format_bulk_data(abstract_keywords_eng, language="eng")
                        try:
                            abstract_keywords_tr = article_element.find_element(By.CLASS_NAME, 'summarySub').text.strip()
                            abstract_tr, keywords_tr = format_bulk_data(abstract_keywords_tr, language="tr")
                        except Exception:
                            pass

                    # Page Range, Article Code, Volume, Issue
                    try:
                        full_reference_text = article_element.find_elements(By.CLASS_NAME, 'altBilgi')[0].text.strip()
                        page_range, article_code, article_volume, article_issue = get_page_range(full_reference_text, pdf_scrape_type)
                    except Exception as e:
                        send_notification(GeneralError(f"Error encountered while getting page range, article code, "))

                    # DOI
                    try:
                        article_doi = article_element.find_element(By.CLASS_NAME, 'doi').text.split(':')[1].strip()
                    except Exception:
                        article_doi = None

                    # Download Link
                    try:
                        pdf_element = article_element.find_element(By.CLASS_NAME, 'pdf')
                        download_link = pdf_element.find_element(By.TAG_NAME, 'a').get_attribute('href')
                    except Exception as e:
                        send_notification(GeneralError(f"No pdf link found for TK article of journal {journal_name} "
                                                       f"(klinikler_no_ref_scraper, klinikler_scrapers). "
                                                       f"Error encountered was: {e}."))
                        download_link = None

                    # Download PDF and send to Azure
                    if download_link:
                        driver.get(download_link)
                        if check_download_finish(download_path):
                            file_name = get_recently_downloaded_file_name(download_path)
                            # Send PDF to Azure and format response
                            if with_azure:
                                first_pages_cropped_pdf = crop_pages(file_name)

                                location_header = AzureHelper.analyse_pdf(
                                    first_pages_cropped_pdf, is_tk=True)  # Location header is the response address of Azure API
                                time.sleep(10)
                                azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                                azure_data = azure_response_dictionary
                                with open("azure_response.json", "w", encoding='utf-8') as outfile:
                                    json.dump(azure_data, outfile, indent=4)
                                azure_article_data = AzureHelper.format_tk_data(azure_data)
                                with open("azure_response_formatted.json", "w", encoding='utf-8') as outfile:
                                    json.dump(azure_article_data, outfile, indent=4)
                            # Send PDF to Adobe and format response
                            if with_adobe:
                                adobe_cropped = split_in_half(file_name)
                                adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                    final_authors = paired_authors
                    if with_azure:
                        correspondence_name, correspondence_mail = azure_article_data.pop("correspondance_name"), \
                            azure_article_data.pop("correspondance_email")
                        final_authors = update_authors_with_correspondence(paired_authors, correspondence_name, correspondence_mail)

                    # IMPORTANT NOTE:
                    # For the final data dictionary I am writing None values for the data that is either cannot be
                    # scraped or not available in the website or if any error is encountered while scraping.
                    final_article_data = {
                        "journalName": f"{journal_name}",
                        "articleType": article_type,
                        "articleTitle": {"TR": turkish_title, "ENG": english_title},
                        "articleAbstracts": {"TR": abstract_tr, "ENG": abstract_eng},
                        "articleKeywords": {"TR": keywords_tr, "ENG": keywords_eng},
                        "articleDOI": article_doi,
                        "articleCode": article_code,
                        "articleYear": datetime.now().year,
                        "articleVolume": article_volume,
                        "articleIssue": article_issue,
                        "articlePageRange": page_range,
                        "articleAuthors": final_authors,
                        "articleReferences": adobe_references if with_adobe else None}
                    if with_azure:
                        final_article_data.update(azure_article_data)
                    pprint.pprint(final_article_data, width=150)
                    i += 1
                    clear_directory(download_path)


if __name__ == '__main__':
    klinikler_no_ref_scraper('foo', 'bar', 'zoo', 'poo')
