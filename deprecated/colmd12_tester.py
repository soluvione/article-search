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
from common.erorrs import GeneralError
from classes.author import Author
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
from scrapers.dergipark_scraper import update_scanned_issues
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from fuzzywuzzy import fuzz
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

with_azure = False
with_adobe = False
json_two_articles = False


def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "../downloads_n_logs",
                             "col_md12_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "../downloads_n_logs",
                                  "col_md12_manual", parent_type,
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
            GeneralError(f"Error encountered while updating col_md12 journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for col_md12 journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for col_md12 journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, col_md12_scraper.py). Error: {e}"))
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
    if not final_article_data["articleDOI"]:
        try:
            doi = azure_article_data.get("doi", "")
            final_article_data["articleDOI"] = doi
            doi = doi[doi.index("/10.") + 1:]
            final_article_data["articleDOI"] = doi
        except:
            pass
    if not final_article_data["articleAuthors"]:
        final_article_data["articleAuthors"] = azure_article_data.get("article_authors", [])
    return final_article_data


def col_md12_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
    i = 0
    # Webdriver options
    # Eager option shortens the load time. Driver also always downloads the pdfs and does not display them
    options = Options()
    options.page_load_strategy = 'eager'
    download_path = "get_downloads_path(parent_type, file_reference)"
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
            driver.get("https://aai.org.tr/abstract.php?id=466")
            time.sleep(3)
            main_element = driver.find_element(By.ID, "icerik-alani")
            soup = BeautifulSoup(main_element.get_attribute("outerHTML"), 'html.parser')
            # el ne bilmiyorum
            # try:
            #     el = soup.find('h2').get_text(strip=True)
            # except:
            #     el = driver.find_element(By.XPATH, '//*[@id="icerik-alani"]/div[2]/div[2]/div[1]').text
            # print(el)

            try:
                authors_element = driver.find_element(By.ID, "authors_div").text.split(',')
            except Exception:
                pass

            def has_sup_with_text(element):
                return element.name == 'span' and element.find('sup') is not None

            span_element = soup.find_all(has_sup_with_text)[0]

            # DOI
            try:
                doi = soup.get_text()[soup.get_text().index("DOI"):].split()[2]
            except Exception:
                doi = None

            # Keywords obtained from the meta tag
            response = requests.get("https://cts.tgcd.org.tr/abstract.php?id=188")
            soup = BeautifulSoup(response.content, 'html.parser')
            meta_tag = soup.find('meta', attrs={'name': 'citation_keywords'})
            if meta_tag:
                keywords = meta_tag['content']

            soup = BeautifulSoup(main_element.get_attribute("outerHTML"), 'html.parser')

            # Abstract
            try:
                abstract = soup.get_text()[
                       soup.get_text().index("DOI") + 20: soup.get_text().index("Keywords")].replace("\n", "")
            except Exception:
                abstract = soup.get_text()[
                           soup.get_text().index("Türkiye") + 20: soup.get_text().index("Anahtar")].replace(
                    "\n", "")

            # Authors and Specialities
            authors, specialities = list(), list()
            try:
                # Author Names
                try:
                    authors_names = driver.find_element(By.ID, "authors_div").text.split(',')
                except:
                    pass
                # Specialities
                n, index = 0, 0
                for char in span_element.get_text().strip():
                    if char.isnumeric() and index > 0:
                        specialities.append(span_element.get_text()[n + 1:index + 1].strip()[1:])
                        n = index
                    if index == len(span_element.get_text().strip()) - 1:
                        specialities.append(span_element.get_text()[n + 1:].strip()[1:])
                    index += 1
                # Author Objects
                for author_name in authors_names:
                    try:
                        new_author = Author(name=author_name[:-1], all_speciality=specialities[int(author_name.strip()[-1])])
                        authors.append(new_author)
                    except Exception:
                        pass
            except Exception as e:
                raise e

            # Download Link
            download_link = urljoin(start_page_url, article_url).replace("abtract", "pdf")

            article_lang = "tr" if "ü" in journal_name or "ğ" in journal_name else "en"
            abbreviation = ""
            final_article_data = {
                "journalName": f"{journal_name}",
                "articleType": identify_article_type(article_types[i - 1], 0),
                "articleDOI": doi,
                "articleCode": abbreviation if abbreviation else None,
                "articleYear": datetime.now().year,
                "articleVolume": recent_volume,
                "articleIssue": 3,
                "articlePageRange": None,
                "articleTitle": {"TR": re.sub(r'[\t\n]', '', titles_text[i-1]).strip() if article_lang == "tr" else None,
                                 "ENG": re.sub(r'[\t\n]', '', titles_text[i-1]).strip() if article_lang == "en" else None},
                "articleAbstracts": {"TR": re.sub(r'[\t\n]', '', abstract).strip() if article_lang == "tr" else None,
                                     "ENG": re.sub(r'[\t\n]', '', abstract).strip() if article_lang == "en" else None},
                "articleKeywords": {"TR": re.sub(r'[\t\n]', '', keywords) if article_lang == "tr" else None,
                                    "ENG": re.sub(r'[\t\n]', '', keywords) if article_lang == "en" else None},
                "articleAuthors": Author.author_to_dict(authors) if authors else [],
                "articleReferences": []}
            pprint.pprint(final_article_data)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    col_md12_scraper("asd", "1", "sadsa", 2, "sa", "sadf")