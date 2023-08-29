# Python libraries
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
from common.helpers.methods.common_scrape_helpers.klinikler_helper import format_bulk_data, get_article_titles, \
    pair_authors, get_page_range
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned, tk_no_ref_is_scanned
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.azure.azure_helper import AzureHelper
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_sms import send_notification
import common.helpers.methods.others
from common.services.tk_api.tk_service import TKServiceWorker
from scrapers.dergipark_scraper import update_scanned_issues
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

is_test = True
json_two_articles = True if is_test else False


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "klinikler_manual", parent_type,
                             file_reference, "logs")
    return logs_path


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


# create_logs(True, get_logs_path(parent_type, file_reference))

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
        send_notification(GeneralError(f"Error encountered while updating TK journal logs file with path = {path_}. "
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
            GeneralError(f"Already scanned issue log creation error for TK journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        pdf_scrape_type = kwargs["pdf_scrape_type"]
        if pdf_scrape_type == "A_KLNK":
            return tk_no_ref_is_scanned(kwargs["issue"], kwargs["logs_path"])
        else:
            return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for TK journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, klinikler_scrapers.py). Error: {e}"))
        raise e


def klinikler_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
    i = 0  # Will be used to distinguish article numbers

    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(start_page_url)
            time.sleep(1.25)
            try:
                volume_items = driver.find_element(By.ID, 'volumeList')
                latest_issue = volume_items.find_elements(By.CLASS_NAME, 'issue')[0]
                # Issue no example for TK no ref journal: (23.03.2023)
                # Issue no example for TK ref journal: 3
                issue_no = latest_issue.find_element(By.CLASS_NAME, 'issueNo').text if pdf_scrape_type == "A_KLNK" \
                    else int(latest_issue.find_element(By.CLASS_NAME, 'issueNo').text.split(' ')[-1])
                # TK no ref journals do not have volume or issue numbers
                volume_no = int(volume_items.find_element(By.CLASS_NAME, 'header').text.split(' ')[-1]) \
                    if pdf_scrape_type.strip() == "A_KLNK & R" \
                    else None
            except Exception as e:
                raise GeneralError(
                    f"Error encountered while retrieving vol-issue data of TK journal with name {journal_name}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=volume_no, issue=issue_no, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                issue_link = latest_issue.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                if pdf_scrape_type == "A_KLNK":
                    login_button_xpath = driver.find_element(By.XPATH,
                                                             '/html/body/div/section/div[2]/div[1]/div/a[1]')
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
                # Get to the not scanned issue page
                driver.get(issue_link)
                time.sleep(7)

                # Scrape URLs
                article_urls = []
                article_list = driver.find_element(By.ID, 'articleList')
                article_elements = article_list.find_elements(By.ID, 'article')
                for item in article_elements:
                    string_to_check = item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').text.strip()
                    string1 = "EDİTÖRDEN"
                    string2 = "ÖN SÖZ"
                    if not (string1.casefold() == string_to_check.casefold() or
                            string2.casefold() == string_to_check.casefold()):
                        article_urls.append(
                            item.find_element(By.CSS_SELECTOR, '.middle .name .nameMain a').get_attribute('href'))

                if not article_urls:
                    raise GeneralError(
                        GeneralError(f'No URLs scraped from TK journal with name: {journal_name}'))

                for article_url in article_urls:
                    with_adobe, with_azure = True, True
                    driver.get(article_url)
                    time.sleep(2)
                    try:
                        # Titles in Turkish and English
                        article_element = driver.find_element(By.ID, 'article')
                        turkish_title, english_title = get_article_titles(article_element)

                        # Article Language
                        article_language = article_element.find_elements(By.CLASS_NAME, 'altBilgi')[1].text.split(':')[
                            1].strip().lower()

                        # Article Type
                        try:
                            article_type = article_element.find_element(By.CLASS_NAME, 'header').text.strip()
                            article_type = ''.join([char for char in article_type if char.isalpha() or char.isspace()])
                        except Exception:
                            if pdf_scrape_type == "A_KLNK":
                                article_type = "BÖLÜMLER"
                            else:
                                article_type = None

                        # Author Names and Specialities
                        authors_element = article_element.find_element(By.CLASS_NAME, 'author')
                        author_names_list = [author.strip() for author in
                                             authors_element.text[: authors_element.text.find('\n')].split(',')]
                        author_specialities = [speciality for speciality in authors_element.text.split('\n')[1:]]
                        paired_authors = pair_authors(author_names_list, author_specialities)

                        # Abstract and Keywords (The order of the languages is not fixed)
                        if article_language == "tr":
                            abstract_keywords_tr = article_element.find_element(By.CLASS_NAME,
                                                                                'summaryMain').text.strip()
                            abstract_tr, keywords_tr = format_bulk_data(abstract_keywords_tr, language="tr")
                            try:
                                abstract_keywords_eng = article_element.find_element(By.CLASS_NAME,
                                                                                     'summarySub').text.strip()
                                abstract_eng, keywords_eng = format_bulk_data(abstract_keywords_eng, language="eng")
                            except Exception:
                                pass
                        else:
                            abstract_keywords_eng = article_element.find_element(By.CLASS_NAME,
                                                                                 'summaryMain').text.strip()
                            abstract_eng, keywords_eng = format_bulk_data(abstract_keywords_eng, language="eng")
                            try:
                                abstract_keywords_tr = article_element.find_element(By.CLASS_NAME,
                                                                                    'summarySub').text.strip()
                                abstract_tr, keywords_tr = format_bulk_data(abstract_keywords_tr, language="tr")
                            except Exception:
                                pass

                        # Page Range, Article Code, Volume, Issue
                        try:
                            full_reference_text = article_element.find_elements(By.CLASS_NAME, 'altBilgi')[
                                0].text.strip()
                            page_range, article_code, article_volume, article_issue = get_page_range(
                                full_reference_text, pdf_scrape_type)
                        except Exception as e:
                            send_notification(
                                GeneralError(f"Error encountered while getting page range, article code, "))

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
                            send_notification(
                                GeneralError(f"No pdf link found for TK article of journal {journal_name} "
                                             f"(klinikler_no_ref_scraper, klinikler_scrapers). "
                                             f"Error encountered was: {e}."))
                            download_link = None
                            if pdf_scrape_type == "A_KLNK":
                                raise e

                        # Download PDF and send to Azure
                        if download_link:
                            driver.get(download_link)
                            if check_download_finish(download_path):
                                file_name = get_recently_downloaded_file_name(download_path)
                                # Send PDF to Azure and format response
                                if with_azure:
                                    first_pages_cropped_pdf = crop_pages(file_name)

                                    location_header = AzureHelper.analyse_pdf(
                                        first_pages_cropped_pdf,
                                        is_tk=True)  # Location header is the response address of Azure API
                                    time.sleep(10)
                                    azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                                    azure_data = azure_response_dictionary
                                    azure_article_data = AzureHelper.format_general_azure_data(azure_data)

                                # Send PDF to Adobe and format response
                                if with_adobe:
                                    adobe_cropped = split_in_half(file_name)
                                    adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                    adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                            else:
                                with_adobe, with_azure = False, False

                        final_authors = paired_authors
                        if with_azure:
                            correspondence_name, correspondence_mail = azure_article_data.pop("correspondance_name"), \
                                azure_article_data.pop("correspondance_email")
                            final_authors = update_authors_with_correspondence(paired_authors, correspondence_name,
                                                                               correspondence_mail)

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
                            "articleCode": journal_name.strip() + f"; {article_volume}({article_issue}): "
                                                                  f"{page_range[0]}-{page_range[1]}",
                            "articleYear": datetime.now().year,
                            "articleVolume": article_volume,
                            "articleIssue": article_issue,
                            "articlePageRange": page_range,
                            "articleAuthors": final_authors,
                            "articleReferences": adobe_references if with_adobe else None,
                            "articleURL": article_url,
                            "base64PDF": ""}

                        if is_test:
                            pprint.pprint(final_article_data)
                        if is_test:
                            pprint.pprint(final_article_data)

                        # Send data to Client API
                        tk_worker = TKServiceWorker()
                        final_article_data["base64PDF"] = tk_worker.encode_base64(file_name)
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
                            f"Passed one article of TK journal {journal_name} with article number {i}. "
                            f"Error encountered was: {e}. Traceback: {tb_str}"))
                        continue

                # Successfully completed the operations
                create_logs(True, get_logs_path(parent_type, file_reference))
                if pdf_scrape_type == "A_KLNK":
                    update_scanned_issues(0, 0,
                                          get_logs_path(parent_type, file_reference),
                                          True, issue_no)
                else:
                    update_scanned_issues(volume_no, issue_no,
                                          get_logs_path(parent_type, file_reference))
                return 590 if is_test else timeit.default_timer() - start_time
            else:  # Already scanned the issue
                log_already_scanned(get_logs_path(parent_type, file_reference))
                return 590 if is_test else 530  # If test, move onto next journal, else wait 30 secs before moving on
    except Exception as e:
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping TK journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
