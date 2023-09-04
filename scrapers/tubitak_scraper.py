import re
import time
import os
import traceback
from datetime import datetime
import glob
import json
import pprint
import timeit

from classes.author import Author
# Local imports
from common.errors import GeneralError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.pdf_cropper import split_in_half
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_notification import send_notification
import common.helpers.methods.others
from common.services.tk_api.tk_service import TKServiceWorker
from scrapers.dergipark_scraper import update_scanned_issues
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService

is_test = True
json_two_articles = True if is_test else False

def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "tubitak_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "tubitak_manual", parent_type,
                                  file_reference, "downloads")
    return downloads_path


def get_recently_downloaded_file_name(download_path, journal_name, article_url):
    """
    Give the full PATH of the most recently downloaded file
    :param journal_name: Name of the journal
    :param article_url: URL of the article page
    :param download_path: PATH of the download folder
    :return: Returns the name of the most recently downloaded file
    """
    time.sleep(2)
    try:
        list_of_files = glob.glob(download_path + '/*')
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file
    except Exception as e:
        send_notification(GeneralError(f"Could not get name of recently downloaded file. Journal name: {journal_name}, "
                                       f"article_url: {article_url}. Error: {e}"))
        return False

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


def create_logs(was_successful: bool, path_: str) -> None:
    """
    Creates a logs file in the given path
    :param was_successful: If the trial was successful, then True, else False
    :param path_: PATH value of logs file
    :return: Nothing
    """
    try:
        logs_file_path = os.path.join(path_, 'logs.json')
        if was_successful:
            with open(logs_file_path, 'r') as logs_file:
                logs_data = json.loads(logs_file.read())
        logs_data.append({'timeOfTrial': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                          'attemptStatus': was_successful})
        with open(logs_file_path, 'w') as logs_file:
            logs_file.write(json.dumps(logs_data, indent=4))

    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while updating tubitak journal logs file with path = {path_}. "
                         f"Error encountered: {e}."))


def log_already_scanned(path_: str):
    """
    This function will create a log file for the already scanned issues.
    :param path_: PATH value of the logs file
    :return: None
    """
    try:
        logs_path = os.path.join(path_, "logs.json")
        with open(logs_path, 'r') as logs_file:
            logs_data = json.loads(logs_file.read())
        logs_data.append({'timeOfTrial': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                          'attemptStatus': 'Already Scanned - No Action Needed'})
        with open(logs_path, 'w') as logs_file:
            logs_file.write(json.dumps(logs_data, indent=4))
    except Exception as e:
        send_notification(
            GeneralError(
                f"Already scanned issue log creation error for tubitak journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for tubitak journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, tubitak_scraper.py). Error: {e}"))
        raise e


def populate_with_azure_data(final_article_data, azure_article_data):
    """
    if there are any missing data, it will be populated with azure data either titles, abstracts or keywords
    :param final_article_data:
    :param azure_article_data:
    :return:
    """
    if not final_article_data["articleTitle"]["TR"]:
        final_article_data["articleTitle"]["TR"] = azure_article_data.get("article_titles", {}).get("tr", "")
    if not final_article_data["articleTitle"]["ENG"]:
        final_article_data["articleTitle"]["ENG"] = azure_article_data.get("article_titles", {}).get("eng", "")
    if not final_article_data["articleAbstracts"]["TR"]:
        tr_abstract = azure_article_data.get("article_abstracts", {}).get("tr#1", "")
        tr_abstract2 = azure_article_data.get("article_abstracts", {}).get("tr#2", "")
        final_article_data["articleAbstracts"]["TR"] = tr_abstract + " " + tr_abstract2
    if not final_article_data["articleAbstracts"]["ENG"]:
        eng_abstract = azure_article_data.get("article_abstracts", {}).get("eng#1", "")
        eng_abstract2 = azure_article_data.get("article_abstracts", {}).get("eng#2", "")
        final_article_data["articleAbstracts"]["ENG"] = eng_abstract + " " + eng_abstract2
    if not final_article_data["articleKeywords"]["TR"]:
        final_article_data["articleKeywords"]["TR"] = azure_article_data.get("article_keywords", {}).get("tr", "")
    if not final_article_data["articleKeywords"]["ENG"]:
        final_article_data["articleKeywords"]["ENG"] = azure_article_data.get("article_keywords", {}).get("eng", "")
    if not final_article_data["articleType"]:
        final_article_data["articleType"] = "ORİJİNAL ARAŞTIRMA"
    if not final_article_data["articleAuthors"]:
        final_article_data["articleAuthors"] = azure_article_data.get("article_authors", [])
    if not final_article_data["articleDOI"]:
        final_article_data["articleDOI"] = azure_article_data.get("doi", None)    
    return final_article_data


def tubitak_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
    # Webdriver options
    # Eager option shortens the load time. Driver also always downloads the pdfs and does not display them
    options = Options()
    options.page_load_strategy = 'eager'
    download_path = get_downloads_path(parent_type, file_reference)
    prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--disable-notifications")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--headless")  # This line enables headless mode
    service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver-linux64/chromedriver")

    # Set start time
    start_time = timeit.default_timer()
    i = 0  # Will be used to distinguish article numbers

    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(check_url(start_page_url))
            time.sleep(2)

            try:
                #Get Vol, Issue and Year from the current issue page
                issue_page_main_element = driver.find_element(By.ID, 'alpha')
                current_issue_text = issue_page_main_element.find_element(By.TAG_NAME, 'h1').text
                numbers = re.findall('[0-9]+', current_issue_text)
                article_year = int(numbers[0])
                recent_volume = int(numbers[1])
                recent_issue = int(numbers[2])

            except Exception as e:
                raise GeneralError(f"Volume, issue or year data of tubitak journal is absent! Error encountered was: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)

            if not is_issue_scanned:
                try:
                    article_elements = driver.find_elements(By.CSS_SELECTOR, 'div[class="doc"]')
                    article_urls = list()
                    for item in article_elements:
                        article_urls.append(
                            item.find_elements(By.TAG_NAME, 'p')[1].find_element(By.TAG_NAME, 'a').get_attribute(
                                'href'))
                    article_urls = article_urls[1:]
                except Exception as e:
                    send_notification(GeneralError(
                        f"Error while getting tubitak article urls of tubitak journal. Error encountered was: {e}"))

                if not article_urls:
                    raise GeneralError(
                        GeneralError(f'No URLs scraped from tubitak journal with name: {journal_name}'))

                for article_url in article_urls:
                    with_adobe, with_azure = True, False
                    driver.get(article_url)
                    time.sleep(2)

                    try:
                        keywords_eng = driver.find_element(By.ID, "keywords").text.strip().split('\n')[-1]
                    except:
                        i += 1
                        continue

                    try:
                        article_title_eng = driver.find_element(By.ID, 'title').text.strip()

                        # Authors
                        authors_elements = driver.find_element(By.ID, 'authors').find_element(By.TAG_NAME,
                                                                                              'p').find_elements(
                            By.TAG_NAME, 'a')
                        author_names = [name.text.strip() for name in authors_elements]

                        author_objects = list()
                        for author_name in author_names:
                            author_objects.append(Author(name=author_name))

                        abstract_eng = driver.find_element(By.ID, 'abstract').text.strip()

                        doi = driver.find_element(By.ID, 'doi').text.strip()
                        article_doi = doi[doi.index("10."):]

                        article_page_range = [driver.find_element(By.ID, 'fpage').find_element(By.TAG_NAME, 'p').text,
                                      driver.find_element(By.ID, 'lpage').find_element(By.TAG_NAME, 'p').text]

                        # Abbreviation
                        abbreviation = "Turk J Vet Anim Sci" if "veterinary" in start_page_url else "Turk J Med Sci"

                        download_link = driver.find_element(By.CSS_SELECTOR,
                                                            'div[class="aside download-button"]').find_element(
                            By.TAG_NAME, 'a').get_attribute('href')

                        references = None
                        if download_link:
                            driver.get(download_link)
                            if check_download_finish(download_path, is_long=True):
                                file_name = get_recently_downloaded_file_name(download_path, journal_name, article_url)
                            if not file_name:
                                with_adobe, with_azure = False, False
                                # Send PDF to Azure and format response
                                if download_link and file_name:
                                    # Send PDF to Adobe and format response
                                    if with_adobe:
                                        adobe_cropped = split_in_half(file_name)
                                        time.sleep(1)
                                        adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                        adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                                        references = adobe_references

                        keywords_tr, abstract_tr, article_title_tr = None, None, None
                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": "ORİJİNAL ARAŞTIRMA",
                            "articleDOI": article_doi,
                            "articleCode": abbreviation + f"; {recent_volume}({recent_issue}): "
                                                          f"{article_page_range[0]}-{article_page_range[1]}",
                            "articleYear": article_year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": article_page_range,
                            "articleTitle": {"TR": article_title_tr,
                                             "ENG": article_title_eng},
                            "articleAbstracts": {"TR": abstract_tr,
                                                 "ENG": abstract_eng},
                            "articleKeywords": {"TR": keywords_tr,
                                                "ENG": keywords_eng},
                            "articleAuthors": Author.author_to_dict(author_objects) if author_objects else [],
                            "articleReferences": references,
                            "articleURL": article_url,
                            "base64PDF": ""}

                        if is_test:
                            pprint.pprint(final_article_data)

                        # Send data to Client API
                        tk_worker = TKServiceWorker()
                        final_article_data["base64PDF"] = tk_worker.encode_base64(file_name)
                        if is_test:
                            response = tk_worker.test_send_data(final_article_data)
                            if isinstance(response, Exception):
                                raise response
                        else:
                            response = tk_worker.send_data(final_article_data)
                            if isinstance(response, Exception):
                                raise response

                        i += 1  # Loop continues with the next article
                        clear_directory(download_path)

                        if is_test and i >= 2:
                            return 590
                    except Exception as e:
                        i += 1
                        clear_directory(download_path)
                        tb_str = traceback.format_exc()
                        send_notification(GeneralError(
                            f"Passed one article of tubitak journal {journal_name} with article number {i}. "
                            f"Error encountered was: {e}. Traceback: {tb_str}"))
                        continue
                # Successfully completed the operations
                create_logs(True, get_logs_path(parent_type, file_reference))
                update_scanned_issues(recent_volume, recent_issue,
                                      get_logs_path(parent_type, file_reference))
                return 590 if is_test else timeit.default_timer() - start_time
            else:  # Already scanned the issue
                log_already_scanned(get_logs_path(parent_type, file_reference))
                return 590 if is_test else 530  # If test, move onto next journal, else wait 30 secs before moving on
    except Exception as e:
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping tubitak journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
