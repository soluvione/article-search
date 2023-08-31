import random
import time
import os
import traceback
from datetime import datetime
import glob
import json
import pprint
import timeit
import re
# Local imports
from classes.author import Author
from common.erorrs import GeneralError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
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
from fuzzywuzzy import fuzz

json_two_articles = False
is_test = True

def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "wolters_kluwer_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "wolters_kluwer_manual", parent_type,
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
            GeneralError(f"Error encountered while updating wolters_kluwer journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for wolters_kluwer journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for wolters_kluwer journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, wolters_kluwer_scraper.py). Error: {e}"))
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
        final_article_data["articleType"] = azure_article_data.get("article_authors", "ORİJİNAL ARAŞTIRMA")
    if not final_article_data["articleAuthors"]:
        final_article_data["articleAuthors"] = azure_article_data.get("article_authors", [])
    if not final_article_data["articleDOI"]:
        final_article_data["articleDOI"] = azure_article_data.get("doi", None)    
    return final_article_data


def wolters_kluwer_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
        with (webdriver.Chrome(service=service, options=options) as driver):
            driver.get(check_url(start_page_url))
            time.sleep(3)

            try:  # Sometimes cookie pop-ups appear
                time.sleep(1)
                driver.find_element(By.CSS_SELECTOR, 'button[id="onetrust-reject-all-handler"]').click()
            except:
                pass


            try:
                current_issue_element = driver.find_element(By.CSS_SELECTOR, 'h3[id^="ctl00"]')
                numbers = [int(number.strip()) for number in re.findall(r'\d+', current_issue_element.text)]
                year = numbers[0]
                recent_volume = numbers[1]
                recent_issue = numbers[2]
            except Exception as e:
                raise GeneralError(
                    f"Volume, issue or year data of wolters_kluwer journal is absent! Error encountered was: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)

            if not is_issue_scanned:
                # Get to the latest issue page
                driver.get(start_page_url.replace("default", "currenttoc"))

                try:  # Pop-up
                    time.sleep(1)
                    driver.find_element(By.CSS_SELECTOR, 'button[id="onetrust-reject-all-handler"]').click()
                except:
                    pass

                article_urls = []
                try:
                    for item in driver.find_element(By.CSS_SELECTOR, 'div[class="article-list"]').find_elements(
                            By.TAG_NAME, 'h4'):
                        article_urls.append(item.find_element(By.TAG_NAME, 'a').get_attribute('href'))
                except Exception as e:
                    raise GeneralError(
                        f"Error while getting wolters_kluwer article URLs of unq_tk journal. Error encountered was: {e}")

                if not article_urls:
                    raise GeneralError(
                        GeneralError(f'No URLs scraped from wolters_kluwer journal with name: {journal_name}'))

                for article_url in article_urls:
                    try:
                        driver.get(article_url)
                        try:  # Pop-up
                            time.sleep(3)
                            driver.find_element(By.CSS_SELECTOR, 'button[id="onetrust-reject-all-handler"]').click()
                        except:
                            pass

                        # Article Type
                        article_type = driver.find_element(By.CSS_SELECTOR, 'div[class="ejp-r-article-subsection__text"]').text.strip()
                        if "editor" in article_type.lower() or "ediror" in article_type.lower():
                            continue
                        article_type = identify_article_type(article_type, 0)

                        # Article Title
                        article_title_eng = driver.find_element(By.CSS_SELECTOR, 'h1[class="ejp-article-title"]').text.replace("\n", "").replace("\t", "").strip()

                        # Abstract
                        try:
                            abstract_eng = driver.find_element(By.CSS_SELECTOR,
                                                           'div[class="ejp-article-text-abstract"]').text.strip()
                        except Exception as e:
                            raise e

                        # Page Range
                        try:
                            bulk_text = driver.find_element(By.CSS_SELECTOR,
                                                            'span[id="ej-journal-date-volume-issue-pg"]').text
                            article_page_range = [int(number.strip()) for number in
                                          bulk_text[bulk_text.index(":p") + 2:bulk_text.index(",")].split('-')]
                        except Exception:
                            article_page_range = None

                        # DOI
                        try:
                            article_doi = driver.find_element(By.CSS_SELECTOR, 'div[class="ej-journal-info"]').text.strip().split()[
                                -1]
                        except Exception:
                            article_doi = None

                        # Authors Section
                        # Sample names: Koothati, Ramesh Kumar; Yendluru, Mercy Sravanthi; Dirasantchu, Suresh; Muvva, Himapavana; Khandare, Samadhan; Kallumatta, Avinash
                        author_objects = list()
                        try:
                            authors_element = driver.find_element(By.CSS_SELECTOR, 'section[id="ejp-article-authors"]')
                            author_names = authors_element.find_element(By.CSS_SELECTOR, 'p[id="P7"]').text.split(';')
                            formatted_author_names = [
                                (name_section.split(',')[1].strip() + ' ' + name_section.split(',')[0].strip()).strip() for
                                name_section in author_names]

                            driver.find_element(By.CSS_SELECTOR, 'a[id="ejp-article-authors-link"]').click()
                            time.sleep(1)
                            main_affiliation_element = driver.find_element(By.CSS_SELECTOR,
                                                                           'div[class="ejp-article-authors-info-holder"]')
                            affiliations = list()
                            correspondence_name, correspondence_email = None, None
                            for affiliation in main_affiliation_element.text.split('\n'):
                                if affiliation.startswith("Address for"):
                                    try:
                                        correspondence_name = affiliation[
                                                              affiliation.index(":") + 1: affiliation.index(",")].strip()
                                    except:
                                        pass
                                    try:
                                        correspondence_email = affiliation.strip().split()[-1]
                                    except:
                                        pass
                                    break
                                else:
                                    affiliations.append(affiliation.strip())

                            # Construct authors objects
                            for author_name in formatted_author_names:
                                author_to_add = Author()
                                author_to_add.name = author_name.strip()[:-1] if author_name.strip()[
                                    -1].isdigit() else author_name.strip()
                                author_to_add.is_correspondence = True if fuzz.ratio(author_to_add.name.lower(),
                                                                                     correspondence_name.lower()) > 80 else False
                                if len(affiliations) == 1:
                                    author_to_add.all_speciality = affiliations[0][1:] if affiliations[0][0].isdigit() else \
                                    affiliations[0]
                                    author_to_add.name = re.sub(r'\d', '', author_to_add.name)
                                else:
                                    try:
                                        try:
                                            affiliation_code = int(re.search(r'\d', author_to_add.name[-1]).group(0))
                                        except:
                                            affiliation_code = 0
                                        for affil in affiliations:
                                            if affil[0].isdigit() and int(affil[0]) == affiliation_code:
                                                author_to_add.all_speciality = affil[1:]
                                        if not author_to_add.all_speciality:
                                            author_to_add.all_speciality = affiliations[0]
                                        author_to_add.name = re.sub(r'\d', '', author_to_add.name)
                                    except Exception as e:
                                        author_to_add.all_speciality = random.choice(affiliations)
                                if author_to_add.is_correspondence:
                                    author_to_add.mail = correspondence_email
                                author_objects.append(author_to_add)
                        except Exception as e:
                            pass

                        try:
                            driver.execute_script("window.scrollBy(0, 10000)")
                            button = driver.find_element(By.CSS_SELECTOR, 'button[class="article-referenreferences__button"]')
                            driver.execute_script("arguments[0].click();", button)
                            time.sleep(3)
                        except Exception as e:
                            raise e

                        references = list()
                        try:
                            references_element = driver.find_element(By.CSS_SELECTOR, 'section[id="article-references"]')
                            reference_elements = references_element.find_elements(By.CSS_SELECTOR,
                                                                       'div[class="article-references__item js-article-reference"]')
                            for reference in reference_elements:
                                references.append(reference.get_attribute('innerHTML')[
                                      :reference.get_attribute('innerHTML').index('<d')].replace("&nbsp;", "").strip())

                            keywords_eng = [keyword.get_attribute('data-value').strip() for keyword in
                                        driver.find_element(By.XPATH, '//*[@id="ej-article-view"]/div/div').find_elements(
                                            By.CSS_SELECTOR, 'span[class="ej-keyword"]')]
                        except Exception as e:
                            raise e

                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_type,
                            "articleDOI": article_doi,
                            "articleCode": journal_name + f"; {recent_volume}({recent_issue}): "
                                                          f"{article_page_range[0]}-{article_page_range[1]}",
                            "articleYear": year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": article_page_range,
                            "articleTitle": {"TR": None,
                                             "ENG": article_title_eng},
                            "articleAbstracts": {"TR": None,
                                                 "ENG": abstract_eng},
                            "articleKeywords": {"TR": None,
                                                "ENG": keywords_eng},
                            "articleAuthors": Author.author_to_dict(author_objects) if author_objects else [],
                            "articleReferences": references if references else [],
                            "articleURL": article_url,
                            "base64PDF": None}

                        if is_test:
                            pprint.pprint(final_article_data)

                        # Send data to Client API
                        tk_worker = TKServiceWorker()
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
                            f"Passed one article of wolters_kluwer journal {journal_name} with article number {i}. "
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping wolters_kluwer journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
