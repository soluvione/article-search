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
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter
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
                             "firat_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "firat_manual", parent_type,
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
            GeneralError(f"Error encountered while updating firat journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for firat journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for firat journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, firat_scraper.py). Error: {e}"))
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


def firat_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
    # Webdriver options
    # Eager option shortens the load time. Driver also always downloads the pdfs and does not display them
    options = Options()
    options.page_load_strategy = 'eager'
    download_path = get_downloads_path(parent_type, file_reference)
    prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--disable-notifications")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--headless")
    service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver-linux64/chromedriver")

    # Set start time
    start_time = timeit.default_timer()
    i = 0  # Will be used to distinguish article numbers

    try:
        with (webdriver.Chrome(service=service, options=options) as driver):
            if not "fusabil" in start_page_url:
                driver.get(check_url(start_page_url))
            else:
                driver.get("http://" + start_page_url)
            time.sleep(5)

            try:
                #Get Vol, Issue and Year from the home page
                try:
                    numbers_text = driver.find_element(By.XPATH,""
                                                       '/html/body/center/table[2]/tbody/tr/td[1]/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]').text
                except:
                    try:
                        numbers_text = driver.find_element(By.XPATH,
                                                           '/html/body/center/table[2]/tbody/tr/td[2]/table/tbody/tr/td/table/tbody/tr[2]/td[2]').text
                    except:
                        try:
                            numbers_text = driver.find_element(By.XPATH,
                                                               '/html/body/center/table[2]/tbody/tr/td[1]/table/tbody/tr[2]/td/table/tbody').text
                        except:
                            try:
                                numbers_text = driver.find_element(By.XPATH,
                                                                   '/html/body/center/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[1]/td[2]/font').text
                            except:
                                numbers_text = driver.find_element(By.XPATH,
                                                                   '/html/body/center/table/tbody/tr[2]/td[2]/table/tbody/tr[1]/td[2]/table/tbody/tr[1]/td[1]/table[2]/tbody/tr[2]/td[2]/font').text

                regex = re.findall(r'\d+', numbers_text)
                article_year = regex[0]
                recent_volume = regex[1]
                recent_issue = regex[2]
            except Exception as e:
                raise GeneralError(f"Volume, issue or year data of firat journal {journal_name} is absent! Error encountered was: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                if is_test:
                    update_scanned_issues(recent_volume, recent_issue,
                                          get_logs_path(parent_type, file_reference))
                try:
                    try:
                        issue_url = driver.find_element(By.XPATH,
                                                  '/html/body/center/table[2]/tbody/tr/td[1]/table/tbody/tr[2]/td/table/tbody/tr[1]/td[3]/a').get_attribute('href')
                        driver.get(issue_url)
                        time.sleep(1)
                    except Exception as e:
                        try:
                            issue_url = driver.find_element(By.XPATH,
                                                      '/html/body/center/table[2]/tbody/tr/td[2]/table/tbody/tr/td/table/tbody/tr[1]/td[3]/a').get_attribute('href')
                            driver.get(issue_url)
                            time.sleep(1)
                        except:
                            try:
                                issue_url = driver.find_element(By.XPATH,
                                                                '/html/body/center/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[1]/td[2]/a').get_attribute(
                                    'href')
                                driver.get(issue_url)
                                time.sleep(1)
                            except:
                                try:
                                    issue_url = driver.find_element(By.XPATH,
                                                                    '/html/body/center/table/tbody/tr[2]/td[2]/table/tbody/tr[1]/td[2]/table/tbody/tr[1]/td[1]/table[2]/tbody/tr[2]/td[2]/a').get_attribute(
                                        'href')
                                    driver.get(issue_url)
                                    time.sleep(1)
                                except:
                                    issue_url = driver.find_element(By.XPATH, '/html/body/center/table/tbody/tr[2]/td[2]/table/tbody/tr[1]/td[2]/table/tbody/tr[1]/td[1]/table[2]/tbody/tr[2]/td[2]/a').get_attribute('href')
                                    driver.get(issue_url)
                                    time.sleep(1)

                except Exception as e:
                    raise GeneralError(
                        f"Error while getting issue URL of firat journal {journal_name}. Error encountered was: {e}")

                article_urls = list()
                try:
                    try:
                        article_elements = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody').find_elements(
                            By.CSS_SELECTOR, 'font[class="blue"]')
                        for el in article_elements:
                            article_urls.append(el.find_element(By.CSS_SELECTOR, 'a[class="blue"]').get_attribute('href'))
                    except:
                        article_elements = driver.find_element(By.XPATH,
                                                               '/html/body/center/table/tbody/tr[2]/td[2]/table/tbody/tr[1]/td[2]/table/tbody/tr/td/table').find_elements(
                            By.CSS_SELECTOR,
                            'font[class="blue"]')
                        for el in article_elements:
                            article_urls.append(el.find_element(By.CSS_SELECTOR, 'a[class="blue"]').get_attribute('href'))
                except Exception as e:
                    send_notification(GeneralError(
                        f"Error while getting article URLs of Fırat journal. Error encountered was: {e}"))
                    raise e

                if not article_urls:
                    raise GeneralError(
                        GeneralError(f'No URLs scraped from firat journal with name: {journal_name}'))

                for article_url in article_urls:
                    with_adobe, with_azure = False, False
                    driver.get(article_url)
                    time.sleep(2)
                    try:
                        main_body_element = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody')
                        main_text = main_body_element.text
                    except Exception:
                        raise GeneralError(
                            f"No main body element of the article of Fırat journal {journal_name} with number {i}"
                            f"found! Error encountered was: {e}")

                    try:
                        try:
                            # Download Link
                            download_link = article_url.replace("text", "pdf")
                        except Exception:
                            download_link = None

                        # Article Title - Only Turkish Available for Fırat Journals
                        article_title_tr = main_body_element.find_element(By.CSS_SELECTOR, 'font[class="head"]').text.strip()

                        # Article Type
                        if "case" in article_title_tr.lower() or "report" in article_title_tr.lower() \
                            or "olgu" in article_title_tr.lower() or "sunum" in article_title_tr.lower():
                            article_type = "OLGU SUNUMU"
                        else:
                            article_type = "ORİJİNAL ARAŞTIRMA"

                        # Abstract - Only Turkish Available for firat Journals
                        abstract_tr = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[9]/td[1]').text.strip() \
                        if not "tmc.dergisi" in start_page_url \
                            else driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[8]/td[1]/font').text.strip()

                        # Keywords - Only Turkish Available for firat Journals
                        keywords_tr = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[7]').text \
                        if not "tmc.dergisi" in start_page_url \
                            else driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[6]/td/font').text
                        keywords_tr = [keyword.strip() for keyword in keywords_tr.strip()[keywords_tr.index(":")+1:].split(',')]

                        # Abbreviation and Page Range
                        if "firattip" in start_page_url:
                            abbreviation = "Firat Med J"
                        elif "veteriner" in start_page_url:
                            abbreviation = "F.U. Vet. J. Health Sci."
                        elif "tmc.dergi" in start_page_url:
                            abbreviation = "Turk Mikrobiyol Cemiy Derg"
                        elif "turkjpath" in start_page_url:
                            abbreviation = "Turkish Journal of Pathology"
                        else:
                            abbreviation = "F.U. Med.J.Health.Sci."

                        try:
                            page_range_text = main_text[main_text.index('Sayfa(lar)') + 10:main_text.index('Sayfa(lar)') + 18]
                            article_page_range = [int(number.strip()) for number in page_range_text.split('-')]
                        except:
                            article_page_range = [0, 1]

                        # Authors
                        author_names = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[5]').text.strip().split(',') \
                        if not "tmc.dergi" in start_page_url \
                        else driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[4]/td').text.strip().split(',')
                        author_affiliations = driver.find_element(By.XPATH,
                                                                  '/html/body/center/table[2]/tbody/tr[6]').text.split('\n') \
                        if not "tmc.dergi" in start_page_url \
                        else driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[5]/td').text.split('\n')

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

                        # DOI
                        article_doi = None  # No DOI can be scraped directly from the article pages

                        # References
                        references = None
                        if not "tmc.dergi" in start_page_url:
                            try:
                                references = main_text[main_text.index("Kaynaklar\n1)"): main_text.index("[ Başa")]
                                references = references[references.index("1)"): references.rfind('.') + 1].split('\n')
                                references = [reference_formatter(reference, True, count) for count, reference in
                                              enumerate(references, start=1)]
                            except Exception:
                                pass

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
                                             "ENG": None},
                            "articleAbstracts": {"TR": abstract_tr,
                                                 "ENG": None},
                            "articleKeywords": {"TR": keywords_tr,
                                                "ENG": None},
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
                            f"Passed one article of - FIRAT - journal {journal_name} with article number {i}. "
                            f"Error encountered was: {e}. Article URL: {article_url}. Traceback: {tb_str}"))
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping firat journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time

