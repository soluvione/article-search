import re
import time
import os
import traceback
from datetime import datetime
import glob
import json
import pprint
import timeit

# Local imports
from common.erorrs import GeneralError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type, reference_formatter
from common.helpers.methods.common_scrape_helpers.other_helpers import check_article_type_pass
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.azure.azure_helper import AzureHelper
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_sms import send_notification
import common.helpers.methods.others
from common.services.tk_api.tk_service import TKServiceWorker
from classes.author import Author
from scrapers.dergipark_scraper import update_scanned_issues
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

with_azure = True
with_adobe = True
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
                             "aves_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "aves_manual", parent_type,
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
            GeneralError(f"Error encountered while updating aves journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for aves journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for aves journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, aves_scraper.py). Error: {e}"))
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
    return final_article_data


def aves_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
    i = 0
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
    service = ChromeService(executable_path=ChromeDriverManager().install())

    # Set start time
    start_time = timeit.default_timer()

    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(check_url(start_page_url))
            time.sleep(10)
            # Scroll to the bottom
            start = timeit.default_timer()
            while timeit.default_timer() - start < 10:
                driver.execute_script("window.scrollBy(0,500)")
                time.sleep(0.2)

            # Go up
            driver.execute_script("window.scrollBy(0,-5000)")
            driver.maximize_window()
            time.sleep(5)

            try:
                numbers = [int(number) for number in
                           re.findall(r'\d+', driver.find_element(By.CSS_SELECTOR, "[class^='article_type_hea']").text)]

                recent_volume, recent_issue, article_year = numbers[0], numbers[1], numbers[2]
            except Exception as e:
                raise GeneralError("Volume, issue or year data of aves journal is absent!")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                article_urls = list()
                try:
                    for item in driver.find_elements(By.CSS_SELECTOR, "[class='article']"):
                        article_urls.append(item.find_element(By.TAG_NAME, 'a').get_attribute('href'))
                except Exception as e:
                    send_notification(GeneralError(
                        f"Error while getting aves article urls of journal: {journal_name}. Error encountered was: {e}"))

                for url in article_urls:
                    with_adobe, with_azure = True, True
                    driver.get(url)
                    time.sleep(5)
                    try:
                        # You need to click on collapsed arrow head to expand the affiliations
                        driver.find_element(By.CSS_SELECTOR, '.reference.collapsed').click()
                        time.sleep(5)

                        try:
                            # Download Link
                            download_link = driver.find_element(By.CLASS_NAME, 'articles').find_element(By.TAG_NAME,
                                                                                                        'a').get_attribute(
                                'href')
                        except Exception:
                            download_link = None

                        # Article Type
                        article_type = identify_article_type(
                            driver.find_element(By.CSS_SELECTOR, "[class^='article_type_hea']").text.strip(), 0)

                        # Article Title - Only English Available for Aves Journals
                        article_title = driver.find_element(By.CLASS_NAME, 'article_content').text.strip()

                        # Abstract - Only English Available for Aves Journals
                        abstract = driver.find_element(By.CSS_SELECTOR, '.content').text.split("Cite this")[0].strip()

                        # Keywords - Only English Available for Aves Journals
                        keywords = driver.find_element(By.CSS_SELECTOR, '.keyword').text.split(':')[-1].strip().split(
                            ',')
                        keywords = [keyword.strip() for keyword in keywords]

                        # Abbreviation and Page Range
                        bulk_text = driver.find_element(By.CSS_SELECTOR, 'div.journal').text
                        abbreviation = re.sub(r'\d+|[:.;-]+', '', bulk_text).strip()
                        article_page_range = [int(number) for number in bulk_text.split()[-1].split('-')]

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
                                author.all_speciality = specilities[int(author_name[-1]) - 1]
                                author.is_correspondence = True if authors_list.index(author_name) == 0 else False
                                authors.append(author)
                            except Exception as e:
                                send_notification(GeneralError(
                                    f"Error while getting aves article authors' data of journal: {journal_name}. Error encountered was: {e}"))

                        # DOI
                        article_doi = driver.find_element(By.CSS_SELECTOR, '.doi').text.split(':')[-1].strip()

                        references = None  # Aves Journals never have references
                        file_name = None
                        if download_link:
                            driver.get(download_link)
                            if check_download_finish(download_path, is_long=True):
                                file_name = get_recently_downloaded_file_name(download_path)
                                # Send PDF to Azure and format response
                                if with_azure:
                                    first_pages_cropped_pdf = crop_pages(file_name, pages_to_send)
                                    location_header = AzureHelper.analyse_pdf(
                                        first_pages_cropped_pdf,
                                        is_tk=False)  # Location header is the response address of Azure API
                            else:
                                with_azure, with_adobe = False, False

                        if download_link and file_name:
                            # Send PDF to Adobe and format response
                            if with_adobe:
                                adobe_cropped = split_in_half(file_name)
                                time.sleep(1)
                                adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                                references = adobe_references

                        # Get Azure Data
                        if download_link and file_name:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                            azure_data = azure_response_dictionary["Data"]
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data)
                            if len(azure_article_data["emails"]) == 1:
                                for author in authors:
                                    author.mail = azure_article_data["emails"][0] if author.is_correspondence else None

                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_type,
                            "articleDOI": article_doi,
                            "articleCode": abbreviation if abbreviation else "",
                            "articleYear": article_year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": article_page_range,
                            "articleTitle": {"TR": None,
                                             "ENG": article_title},
                            "articleAbstracts": {"TR": None,
                                                 "ENG": abstract},
                            "articleKeywords": {"TR": None,
                                                "ENG": keywords},
                            "articleAuthors": Author.author_to_dict(authors) if authors else [],
                            "articleReferences": references}
                        if with_azure:
                            final_article_data = populate_with_azure_data(final_article_data, azure_article_data)
                        pprint.pprint(final_article_data)

                        # Send data to Client API
                        tk_worker = TKServiceWorker()
                        response = tk_worker.send_data(final_article_data)
                        if isinstance(response, Exception):
                            clear_directory(download_path)
                            raise response

                        i += 1  # Loop continues with the next article
                        clear_directory(download_path)
                    except Exception as e:
                        tb_str = traceback.format_exc()
                        send_notification(GeneralError(
                            f"Passed one article of aves journal {journal_name} with article number {i}. "
                            f"Error encountered was: {e}. Traceback: {tb_str}"))
                        clear_directory(download_path)
                        i += 1
                        continue

                create_logs(True, get_logs_path(parent_type, file_reference))
                # Update the most recently scanned issue according to the journal type
                update_scanned_issues(recent_volume, recent_issue,
                                      get_logs_path(parent_type, file_reference))
                return 590 if is_test else timeit.default_timer() - start_time
            else:  # Already scanned the issue
                log_already_scanned(get_logs_path(parent_type, file_reference))
                return 590 if is_test else 530  # If test, move onto next journal, else wait 30 secs before moving on

    except Exception as e:
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping aves journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
