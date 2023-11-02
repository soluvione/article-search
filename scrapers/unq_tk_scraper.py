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
from common.errors import GeneralError
from classes.author import Author
from common.enums import AzureResponse
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type, reference_formatter
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.pdf_cropper import crop_pages
from common.services.azure.azure_helper import AzureHelper
from common.services.send_notification import send_notification
import common.helpers.methods.others
from common.services.tk_api.tk_service import TKServiceWorker
from scrapers.dergipark_scraper import update_scanned_issues
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService

is_test = False
json_two_articles = True if is_test else False


def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "unq_tk_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "unq_tk_manual", parent_type,
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
            GeneralError(f"Error encountered while updating unq_tk journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for unq_tk journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for unq_tk journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, unq_tk_scraper.py). Error: {e}"))
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


def unq_tk_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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

    # Notlar
    # jpmrs VE tjrms ÇİFT DİLLİ, journalofoncology TEK DİLLİ İNGİLİZCE
    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(check_url(start_page_url))
            time.sleep(10)
            try:
                # Get Vol, Issue and Year from the home page
                if not "journalofoncology" in start_page_url and not "jcog" in start_page_url:
                    recent_issue_text = driver.find_element(By.CSS_SELECTOR,
                                                            'div[class^="issue-details col-md-4"]').text
                else:
                    recent_issue_text = driver.find_element(By.CSS_SELECTOR,
                                                            'div[class^="issue-bar issue-bar-right"]').text

                numbers = re.findall('[0-9]+', recent_issue_text)
                article_year = int(numbers[0])
                recent_volume = int(numbers[1])
                recent_issue = int(numbers[2])

            except Exception as e:
                raise GeneralError(
                    f"Volume, issue or year data of unq_tk journal is absent! Error encountered was: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                if is_test:
                    update_scanned_issues(recent_volume, recent_issue,
                                          get_logs_path(parent_type, file_reference))
                # No need to go separate issue pag
                article_urls = list()
                try:
                    article_urls = [element.find_element(By.TAG_NAME, 'a').get_attribute('href') for element in
                                    driver.find_elements(By.CSS_SELECTOR, 'span[class="article_name"]')]
                except Exception as e:
                    raise GeneralError(
                        f"Error while getting unq_tk article URLs of unq_tk journal. Error encountered was: {e}")

                if not article_urls:
                    raise GeneralError(
                        GeneralError(f'No URLs scraped from unq_tk journal with name: {journal_name}'))

                for article_url in article_urls:
                    with_adobe, with_azure = False, True  # UNQ TK journals have the references listed
                    driver.get(article_url)
                    time.sleep(2)
                    try:
                        main_element = driver.find_element(By.CSS_SELECTOR,
                                                           'div[class="col-md-12 category-panel"]') \
                            if "journalofoncology" in start_page_url or "jcog" in start_page_url \
                            else driver.find_element(
                            By.CSS_SELECTOR, 'div[class="col-md-10"]')
                    except Exception as e:
                        raise GeneralError(
                            f"No main body element of the article of unq_tk journal found! Error encountered was: {e}")

                    try:
                        # Article Type
                        article_type = main_element.find_element(By.CSS_SELECTOR,
                                                                 'div[class="bold-medium blue-light-back"]').text \
                            if not ("journalofoncology" in start_page_url or "jcog" in start_page_url) \
                            else driver.find_element(
                            By.CSS_SELECTOR, 'div[class="category-panel-name"]').text.strip()
                        article_type = identify_article_type(article_type, 0)

                        # Authors
                        author_names = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-author"]')[
                            0].text.split(',')

                        try:
                            author_affiliations_data = \
                            main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-author"]')[1].text
                        except:
                            author_names = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-author"]')[
                                0].text.replace("\n", " ")

                            # Find the index of the pattern
                            match = re.search(r'[a-z][A-ZİÖÇ]', author_names)
                            if match:
                                split_index = match.start()
                                author_affiliations_data = author_names[split_index:]
                                author_names = author_names[:split_index].split(",")
                            else:
                                author_affiliations_data = ""

                        author_affiliations = list()
                        array = [author_affiliations_data.index(found) for found in
                                 re.findall('[a-z][A-Z]', author_affiliations_data)]
                        for k in range(len(array)):
                            try:
                                author_affiliations.append(author_affiliations_data[array[k]: array[k + 1]][1:])
                            except:
                                author_affiliations.append(author_affiliations_data[array[-1]:][1:])

                        author_objects = list()
                        for name in author_names:
                            author = Author(name=name.strip()[:-1])
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
                                author.name = re.sub(r"[^a-zA-ZşüğıöçŞÜĞIİÖÇ\s]", "", author.name)
                                author_objects.append(author)
                            except Exception:
                                author.name = re.sub(r"[^a-zA-ZşüğıöçŞÜĞIİÖÇ\s]", "", author.name)
                                author_objects.append(author)

                        # DOI
                        article_doi = main_element.find_element(By.CSS_SELECTOR,
                                                                'div[class="article-doi"]').text.split()[1].strip()

                        # References
                        try:
                            reference_elements = main_element.find_element(By.TAG_NAME, 'ol').find_elements(By.TAG_NAME,
                                                                                                            'li')
                            references = [reference_formatter(element.text, False, count) for count, element in
                                          enumerate(reference_elements, start=1)]
                        except Exception:
                            references = None

                        # Page Range
                        article_page_range = [range.strip() for range in main_element.find_element(By.CSS_SELECTOR,
                                                                                                   'div[class=article-subinfo]').text.split(
                            ':')[-1].split('-')]
                        if int(article_page_range[0]) > int(article_page_range[1]):
                            article_page_range[1] = str(int(article_page_range[0][:-1]) + int(article_page_range[1]))

                        if not ("journalofoncology" in start_page_url or "jcog" in start_page_url):
                            # ÇİFT DİLLİLER
                            article_title_tr = main_element.find_element(By.CSS_SELECTOR,
                                                                         'div[class="article-title"]').text.strip()
                            article_title_eng = main_element.find_element(By.CSS_SELECTOR,
                                                                          'div[class="article-title-second"]').text.strip()
                            try:
                                keywords_tr = main_element.find_element(By.CSS_SELECTOR,
                                                                        'div[class="article-keywords"]').text.strip()
                                keywords_tr = [keyword.strip() for keyword in
                                               keywords_tr[keywords_tr.index(":") + 1:].strip().split(";")]

                                keywords_eng = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-keywords"]')[
                                    -1].text.strip()
                                keywords_eng = [keyword.strip() for keyword in
                                                keywords_eng[keywords_eng.index(":") + 1:].strip().split(";")]
                            except Exception:
                                i += 1
                                continue

                            abstract_tr = main_element.find_element(By.CSS_SELECTOR,
                                                                    'div[class="article-abstract"]').text.strip()
                            abstract_eng = main_element.find_elements(By.CSS_SELECTOR, 'div[class="article-abstract"]')[
                                1].text.strip()

                        else:
                            article_title_eng = main_element.find_element(By.CSS_SELECTOR,
                                                                          'div[class="article-title"]').text.strip()
                            article_title_tr = None
                            try:
                                keywords_eng = main_element.find_element(By.CSS_SELECTOR,
                                                                         'div[class="article-keywords"]').text.strip()
                                keywords_eng = [keyword.strip() for keyword in
                                                keywords_eng[keywords_eng.index(":") + 1:].strip().split(";")]
                                keywords_tr = None
                            except Exception:
                                i += 1
                                continue

                            abstract_eng = main_element.find_element(By.CSS_SELECTOR,
                                                                     'div[class="article-abstract"]').text.strip()
                            abstract_tr = None

                        # Abbreviations
                        if "tjrms" in start_page_url:
                            abbreviation = "TJRMS."
                        elif "jpmrs" in start_page_url:
                            abbreviation = "J PMR Sci."
                        elif "jcog" in start_page_url:
                            abbreviation = "JCOG."
                        else:
                            abbreviation = "J Oncol Sci."

                        download_button = driver.find_element(By.CSS_SELECTOR, 'a[target="_blank"][class^="btn btn"]')
                        download_link = download_button.get_attribute('href')

                        file_name = None
                        if download_link:
                            driver.get(download_link)
                            if check_download_finish(download_path, is_long=True):
                                file_name = get_recently_downloaded_file_name(download_path, journal_name, article_url)
                            if not file_name:
                                with_adobe, with_azure = False, False
                            # Send PDF to Azure and format response
                            if with_azure:
                                first_pages_cropped_pdf = crop_pages(file_name, pages_to_send)
                                location_header = AzureHelper.analyse_pdf(
                                    first_pages_cropped_pdf,
                                    is_tk=False)  # Location header is the response address of Azure API

                        # Get Azure Data
                        azure_article_data = None
                        if download_link and file_name and with_azure:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 60)
                            if azure_response_dictionary["Result"] != AzureResponse.FAILURE.value:
                                azure_data = azure_response_dictionary["Data"]
                                azure_article_data = AzureHelper.format_general_azure_data(azure_data)
                                if len(azure_article_data["emails"]) == 1:
                                    for author in author_objects:
                                        author.mail = azure_article_data["emails"][0] if author.is_correspondence else None
                            else:
                                with_azure = False

                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_type,
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
                            "temporaryPDF": ""}

                        if with_azure:
                            final_article_data = populate_with_azure_data(final_article_data, azure_article_data)
                        if is_test:
                            pprint.pprint(final_article_data)

                        # Send data to Client API
                        tk_worker = TKServiceWorker()
                        final_article_data["temporaryPDF"] = tk_worker.encode_base64(file_name)
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
                            f"Passed one article of - UQN_TK - journal {journal_name} with article number {i}. "
                            f"Error encountered was: {e}. Article URL: {article_url}.  Traceback: {tb_str}"))
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping unq_tk journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
