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
from common.erorrs import GeneralError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type, reference_formatter
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.pdf_cropper import crop_pages
from common.services.azure.azure_helper import AzureHelper
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


def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "span9_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "span9_manual", parent_type,
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
            GeneralError(f"Error encountered while updating span9 journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for span9 journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for span9 journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, span9_scraper.py). Error: {e}"))
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


def span9_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
    service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")

    # Set start time
    start_time = timeit.default_timer()
    i = 0  # Will be used to distinguish article numbers

    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            if not "parkinson" in start_page_url:
                to_go = check_url(start_page_url + "/current-issue")
            else:
                to_go = check_url(start_page_url + "/tur/son-sayi")
            driver.get(to_go)
            time.sleep(2)

            try:
                #Get Vol, Issue and Year from the current issue page
                current_issue_element = driver.find_element(By.CSS_SELECTOR, 'div[class="page-header"]')
                numbers = re.findall('[0-9]+', current_issue_element.text)
                article_year = int(numbers[0])
                recent_volume = int(numbers[1])
                recent_issue = int(numbers[2])

            except Exception as e:
                raise GeneralError(f"Volume, issue or year data of span9 journal is absent! Error encountered was: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)

            if not is_issue_scanned:
                try:
                    main_articles_element = driver.find_element(By.CSS_SELECTOR,
                                                                'div[class="span9"]') if not "jsurg" in start_page_url else driver.find_element(
                        By.CSS_SELECTOR, 'div[class="span12"]')
                    article_elements = main_articles_element.find_elements(By.TAG_NAME, 'h3')
                    article_urls = list()
                    for article_element in article_elements:
                        article_urls.append(article_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
                except Exception as e:
                    send_notification(GeneralError(
                        f"Error while getting span9 article urls of span9 journal. Error encountered was: {e}"))

                if not article_urls:
                    raise GeneralError(
                        GeneralError(f'No URLs scraped from span9 journal with name: {journal_name}'))

                for article_url in article_urls:
                    with_adobe, with_azure = False, True
                    driver.get(article_url)
                    time.sleep(2)
                    try:
                        if not "parkinson" in start_page_url:
                            full_text_page = article_url.replace("abstract", "full-text")
                        else:
                            if not article_url.endswith("tur"):
                                full_text_page = article_url.replace("ozet", "tam-metin")
                            else:
                                full_text_page = article_url

                        driver.get(full_text_page)
                    except Exception as e:
                        raise GeneralError(
                            f"Could not get to the full_text_page of span9 journal found! Error encountered was: {e}")

                    try:
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

                        try:
                            key = meta_element.find_elements(By.TAG_NAME, 'p')[2].text
                        except:
                            try:
                                key = driver.find_element(By.ID, 'article-abstract').find_elements(By.TAG_NAME, 'p')[
                                    -1].text
                            except:
                                continue

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
                        article_doi = doi[doi.index(":") + 1:].strip()
                        article_type = right_bar.find_elements(By.TAG_NAME, 'p')[3].text
                        article_type = identify_article_type(article_type[article_type.index(":") + 1:].strip(), 0)

                        references = [reference_formatter(reference, True, count)
                                      for count, reference
                                      in enumerate(driver.find_element(By.ID, 'article-references').text.split('\n'),
                                                   start=1)
                                      if reference_formatter(reference, True, count)]

                        download_link = full_text_page.replace("full-text", "full-text-pdf") if not "parkinson" in start_page_url else full_text_page.replace("tam-metin", "tam-metin-pdf")

                        # Abbreviation
                        if "parkinson" in start_page_url:
                            abbreviation = "Parkinson Hast Harek Boz Derg."
                        elif "journalofsportsmedicine" in start_page_url:
                            abbreviation = "TurkJ Sports Med."
                        elif "turkjsurg" in start_page_url:
                            abbreviation = "Turk J Surg"
                        else:
                            abbreviation = "Arch Rheumatol"

                        # only_english = "turkjsurg, archivesofrheumatology"
                        # base_turkish = "parkinson"
                        # bu ilk bulunanlar dergi diline göre burada dağıtılacak.
                        if not "parkinson" in start_page_url:
                            article_title_eng = article_title
                            keywords_eng = [keyword.strip() for keyword in key[key.index(":") + 1:].split(',')]
                            abstract_eng = abstract
                        else:
                            article_title_tr = article_title
                            keywords_tr = [keyword.strip() for keyword in key[key.index(":") + 1:].split(',')]
                            abstract_tr = abstract

                        if not "turkjsurg" in start_page_url and not "archivesofrheumatology" in start_page_url:
                            # then there are turkish parts to be scraped
                            if "parkinson" in start_page_url:
                                new_url = full_text_page.replace("tam-metin", "ozet")[:-4]
                                driver.get(new_url)
                                time.sleep(0.5)
                                meta_element = driver.find_element(By.ID, 'article-meta')
                                keywords_eng = meta_element.find_elements(By.TAG_NAME, 'p')[2].text.strip()
                                keywords_eng = [keyword.strip() for keyword in
                                                keywords_eng[keywords_eng.index(":") + 1:].split(',')]
                                article_title_eng = driver.find_element(By.CLASS_NAME, 'page-header').text.strip()
                                abstract_eng = driver.find_element(By.XPATH, '//*[@id="article_abstract"]').text.strip()

                            else:
                                new_url = full_text_page.replace("full-text", "abstract").replace("eng", "tur")
                                driver.get(new_url)
                                time.sleep(0.5)
                                meta_element = driver.find_element(By.ID, 'article-meta')
                                abstract_tr = driver.find_element(By.ID, 'article_abstract').text.strip()
                                keywords_tr = meta_element.find_elements(By.TAG_NAME, 'p')[2].text.strip()
                                keywords_tr = [keyword.strip() for keyword in
                                               keywords_tr[keywords_tr.index(":") + 1:].split(",")]
                                article_title_tr = driver.find_element(By.CLASS_NAME, 'page-header').text.strip()
                        else:
                            article_title_tr = None
                            keywords_tr = None
                            abstract_tr = None


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

                        # Get Azure Data
                        if download_link and file_name and with_azure:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                            azure_data = azure_response_dictionary["Data"]
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data)
                            if len(azure_article_data["emails"]) == 1:
                                for author in author_objects:
                                    author.mail = azure_article_data["emails"][0] if author.is_correspondence else None

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
                            "base64PDF": ""}

                        if with_azure:
                            final_article_data = populate_with_azure_data(final_article_data, azure_article_data)
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
                            f"Passed one article of span9 journal {journal_name} with article number {i}. "
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping span9 journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
