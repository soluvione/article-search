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
from common.errors import GeneralError
from classes.author import Author
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type, reference_formatter
from common.helpers.methods.common_scrape_helpers.other_helpers import check_article_type_pass
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.azure.azure_helper import AzureHelper
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
from fuzzywuzzy import fuzz

is_test = False
json_two_articles = False


def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "pkp_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "pkp_manual", parent_type,
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
            GeneralError(f"Error encountered while updating pkp journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for pkp journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for pkp journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, pkp_scraper.py). Error: {e}"))
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
    if not final_article_data["articleDOI"]:
        final_article_data["articleDOI"] = azure_article_data.get("doi", None)    
    return final_article_data


def pkp_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
    service = ChromeService(executable_path="/home/ubuntu/driver/chromedriver-linux64/chromedriver")

    # Set start time
    start_time = timeit.default_timer()
    i = 0  # Will be used to distinguish article numbers

    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            driver.get(check_url(start_page_url))
            time.sleep(3)
            # Dergiler çok sorunlu ve birbirinden çok farklı arşiv sayfalarına sahip olduğu için bu kısım karışık
            if "saglikokur" in start_page_url:
                driver.find_element(By.XPATH, '//*[@id="navigationPrimary"]/li[3]/a').click()
                time.sleep(7)
                recent_vol_issue_text = driver.find_element(By.XPATH, '/html/body/div/div[1]/div[1]/div/h1').text
                numbers = re.findall(r'\d+', recent_vol_issue_text)
                recent_volume, recent_issue = numbers[0], numbers[1]
                volume_link = ""
            else:
                try:
                    article_issues_element = driver.find_element(By.CSS_SELECTOR, 'ul[class="issues_archive"]')
                    if "eurjther" in start_page_url:
                        elements = driver.find_element(By.CLASS_NAME, "issues_archive").find_elements(By.TAG_NAME, "li")
                        recent_vol_issue_text = elements[2].find_element(By.CLASS_NAME, "title").text
                        volume_link = elements[2].find_element(By.CLASS_NAME, "title").get_attribute("href")
                    elif "natprobiotech" in start_page_url:
                        elements = driver.find_element(By.CLASS_NAME, "issues_archive").find_elements(By.TAG_NAME, "li")
                        recent_vol_issue_text = elements[-1].find_element(By.CLASS_NAME, "title").text
                        volume_link = elements[-1].find_element(By.CLASS_NAME, "title").get_attribute("href")
                    elif "jicah" in start_page_url:
                        recent_issue_element = article_issues_element.find_element(By.CLASS_NAME, 'obj_issue_summary')
                        volume_link = recent_issue_element.find_element(By.CLASS_NAME, 'title').get_attribute('href')
                        recent_vol_issue_text = recent_issue_element.find_element(By.CLASS_NAME, 'series').text
                    else:
                        if "beslenmevediyetdergisi" in start_page_url or "actamedica" in start_page_url:
                            recent_vol_issue_text = article_issues_element.find_element(By.TAG_NAME,
                                                                                        "h2").text
                            volume_link = article_issues_element.find_element(By.TAG_NAME,
                                                                              "h2").find_element(By.TAG_NAME, "a").get_attribute("href")
                        else:
                            recent_vol_issue_text = article_issues_element.find_element(By.CLASS_NAME, "series").text
                            if "injector" in start_page_url:
                                volume_link = article_issues_element.find_element(By.CSS_SELECTOR, 'a[class="title"]').get_attribute("href")
                            else:
                                volume_link = article_issues_element.find_element(By.CLASS_NAME, "title").get_attribute("href")\
                                if "press" not in article_issues_element.find_element(By.CLASS_NAME, "title").text else None


                    numbers = re.findall(r'\d+', recent_vol_issue_text)
                    numbers = [int(n) for n in numbers]
                    recent_volume, recent_issue = numbers[:2]

                    if not volume_link:
                        raise GeneralError(f"No volume_link found for the journal {journal_name}")
                except Exception as e:
                    try:
                        article_issues_element = driver.find_element(By.CSS_SELECTOR, 'div[class="issues media-list"]')
                        recent_vol_issue_text = article_issues_element.find_element(By.TAG_NAME,
                                                                                    "h2").text
                        volume_link = article_issues_element.find_element(By.TAG_NAME,
                                                                          "h2").find_element(By.TAG_NAME,
                                                                                             "a").get_attribute("href")

                        numbers = re.findall(r'\d+', recent_vol_issue_text)
                        numbers = [int(n) for n in numbers]
                        recent_volume, recent_issue = numbers[:2]

                        if not volume_link:
                            raise GeneralError(f"No volume_link found for the journal {journal_name}")
                    except:
                        raise GeneralError(f"An error occurred while retrieving the vol-issue data of PKP journal {journal_name}."
                                            f"Error encountered: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                if is_test:
                    update_scanned_issues(recent_volume, recent_issue,
                                          get_logs_path(parent_type, file_reference))
                if not "saglikokur" in start_page_url:
                    driver.get(volume_link)
                    time.sleep(2)
                article_urls = list()
                try:
                    article_sections_element = driver.find_element(By.CLASS_NAME, "sections")
                    page_ranges, article_types = list(), list()
                    for article_section in article_sections_element.find_elements(By.CLASS_NAME, "section"):
                        section_elements = list()
                        if check_article_type_pass(
                                identify_article_type(article_section.find_element(By.TAG_NAME, "h2").text, 0)):
                            section_elements = article_section.find_elements(By.CLASS_NAME, "obj_article_summary")
                        for section_element in section_elements:
                            article_urls.append(section_element.find_element(By.TAG_NAME, "a").get_attribute("href"))
                            try:
                                page_ranges.append(section_element.find_element(By.CLASS_NAME, "pages").text.strip())
                            except Exception:
                                page_ranges.append("1-12")
                            article_types.append(
                                identify_article_type(article_section.find_element(By.TAG_NAME, "h2").text, 0))
                except Exception as e:
                    raise GeneralError(f"An error occurred while getting article URLs of PKP journal {journal_name}. Error"
                                       f"encountered: {e}")

                for article_url in article_urls:
                    with_adobe, with_azure = False, False
                    try:
                        driver.get(article_url)
                        time.sleep(3)
                        article_element = driver.find_element(By.CLASS_NAME, "obj_article_details")
                        try:
                            english_page = driver.find_element(By.CSS_SELECTOR, "[class^='locale_en_US']")
                            article_language_number = 2
                        except Exception:
                            article_language_number = 1

                        authors = list()
                        # Authors
                        try:
                            authors_element = article_element.find_element(By.CSS_SELECTOR, ".item.authors")
                            for author_element in authors_element.find_elements(By.TAG_NAME, "li"):
                                author = Author()
                                author.name = author_element.find_element(By.CLASS_NAME, "name").text.strip()
                                try:
                                    author.all_speciality = author_element.find_element(By.CLASS_NAME,
                                                                                        "affiliation").text.strip()
                                except Exception:
                                    author.all_speciality = "Format dışı ya da hatalı yazar bilgisi."
                                author.name = re.sub(r"[^a-zA-ZşüğıöçŞÜĞIÖÇ\s]", "", author.name)
                                authors.append(author)
                        except Exception as e:
                            raise e

                        # References
                        references = []
                        try:
                            references_element = article_element.find_element(By.CSS_SELECTOR,
                                                                              ".item.references").find_element(
                                By.CLASS_NAME, "value")
                            for reference_item in references_element.find_elements(By.TAG_NAME, "p"):
                                references.append(reference_item.text.strip())
                            references = [reference_formatter(reference, False, count) for count, reference in
                                          enumerate(references, start=1)]
                        except Exception:
                            pass

                        if not references:
                            with_adobe = True

                        # DOI
                        try:
                            doi = article_element.find_element(By.CSS_SELECTOR, ".item.doi").find_element(By.CLASS_NAME,
                                                                                                          "value").text.strip()
                            doi = doi[doi.index("/10.") + 1:]
                        except Exception:
                            doi = ""

                        try:
                            # Download Link
                            download_link = article_element.find_element(By.CSS_SELECTOR,
                                                                         ".obj_galley_link.pdf").get_attribute("href")
                            download_link = download_link.replace("view", "download")
                        except Exception:
                            download_link = None

                        # Download, crop and send to Azure Form Recognizer Endpoint
                        file_name = None
                        if download_link:
                            driver.get(download_link)
                            if check_download_finish(download_path):
                                file_name = get_recently_downloaded_file_name(download_path, journal_name, article_url)
                            if not file_name:
                                with_adobe, with_azure = False, False
                            # Send PDF to Azure and format response
                            if with_azure:
                                first_pages_cropped_pdf = crop_pages(file_name, pages_to_send)
                                location_header = AzureHelper.analyse_pdf(
                                    first_pages_cropped_pdf,
                                    is_tk=False)  # Location header is the response address of Azure API

                        if article_language_number == 1:
                            article_page_language = "en"
                            navigation_bar_text = driver.find_element(By.CLASS_NAME, "cmp_breadcrumbs").text
                            if "Arşivler" in navigation_bar_text:
                                article_page_language = "tr"

                            article_element = driver.find_element(By.CLASS_NAME, "obj_article_details")
                            article_title_tr = article_element.find_element(By.CLASS_NAME, "page_title").text.strip() \
                                if article_page_language == "tr" else None
                            article_title_eng = article_element.find_element(By.CLASS_NAME, "page_title").text.strip() \
                                if article_page_language == "en" else None
                            # Abstract
                            try:
                                abstract_tr = article_element.find_element(By.CSS_SELECTOR, ".item.abstract") \
                                    .find_element(By.CLASS_NAME, "value").text.strip() \
                                    if article_page_language == "tr" \
                                    else None
                                abstract_eng = article_element.find_element(By.CSS_SELECTOR, ".item.abstract") \
                                    .find_element(By.CLASS_NAME, "value").text.strip() \
                                    if article_page_language == "en" \
                                    else None
                            except Exception:
                                abstract_tr = article_element.find_element(By.CSS_SELECTOR,
                                                                           ".item.abstract").text.strip() \
                                    if article_page_language == "tr" \
                                    else None
                                abstract_eng = article_element.find_element(By.CSS_SELECTOR,
                                                                            ".item.abstract").text.strip() \
                                    if article_page_language == "en" \
                                    else None
                            # Keywords
                            try:
                                keywords = article_element.find_element(By.CSS_SELECTOR, ".item.keywords").find_element(
                                    By.CLASS_NAME, "value").text.strip()
                                keywords_tr = [keyword.strip() for keyword in keywords.split(",")] \
                                    if article_page_language == "tr" \
                                    else None
                                keywords_eng = [keyword.strip() for keyword in keywords.split(",")] \
                                    if article_page_language == "en" \
                                    else None
                            except Exception:
                                keywords = ""

                        else:
                            # Scrape English first by clicking English button
                            driver.find_element(By.CSS_SELECTOR, "[class^='locale_en']").find_element(By.TAG_NAME,
                                                                                                      "a").click()
                            time.sleep(2)
                            article_element = driver.find_element(By.CLASS_NAME, "obj_article_details")
                            # Title
                            article_title_eng = article_element.find_element(By.CLASS_NAME, "page_title").text.strip()
                            # Abstract
                            try:
                                abstract_eng = article_element.find_element(By.CSS_SELECTOR, ".item.abstract") \
                                    .find_element(By.CLASS_NAME, "value").text.strip()
                            except Exception:
                                abstract_eng = article_element.find_element(By.CSS_SELECTOR,
                                                                            ".item.abstract").text.strip()
                            # Keywords
                            try:
                                keywords = article_element.find_element(By.CSS_SELECTOR, ".item.keywords").find_element(
                                    By.CLASS_NAME, "value").text.strip()
                                keywords_eng = [keyword.strip() for keyword in keywords.split(",")]
                            except Exception:
                                keywords = ""
                            # Scrape Turkish content
                            driver.find_element(By.CSS_SELECTOR, "[class^='locale_tr']").find_element(By.TAG_NAME,
                                                                                                      "a").click()
                            time.sleep(2)
                            article_element = driver.find_element(By.CLASS_NAME, "obj_article_details")
                            # Title
                            article_title_tr = article_element.find_element(By.CLASS_NAME, "page_title").text.strip()
                            # Abstract
                            try:
                                abstract_tr = article_element.find_element(By.CSS_SELECTOR, ".item.abstract") \
                                    .find_element(By.CLASS_NAME, "value").text.strip()
                            except Exception:
                                abstract_tr = article_element.find_element(By.CSS_SELECTOR,
                                                                            ".item.abstract").text.strip()
                            # Keywords
                            try:
                                keywords = article_element.find_element(By.CSS_SELECTOR, ".item.keywords").find_element(
                                    By.CLASS_NAME, "value").text.strip()
                                keywords_tr = [keyword.strip() for keyword in keywords.split(",")]
                            except Exception:
                                keywords_tr = ""

                        # Page range
                        try:
                            article_page_range = [int(page_ranges[i].split('-')[0].strip()),
                                                  int(page_ranges[i].split('-')[1].strip())]
                        except Exception:
                            article_page_range = [0, 1]

                        if download_link and with_adobe:
                            # Send PDF to Adobe and format response
                            if with_adobe:
                                adobe_cropped = split_in_half(file_name)
                                adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                                references = adobe_references

                        # Get Azure Data
                        if with_azure:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                            azure_data = azure_response_dictionary["Data"]
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data)
                            success = False
                            mail = ""
                            if len(azure_article_data["emails"]) == 1:
                                try:
                                    mail = azure_article_data["emails"][0][:azure_article_data["emails"][0].index("@")]
                                except Exception as e:
                                    pass
                                if mail:
                                    for author in authors:
                                        if fuzz.ratio(author.name.lower(), mail) > 70:
                                            author.mail = azure_article_data["emails"][0]
                                            author.is_correspondence = True
                                            success = True
                                            break
                            if not success and mail:
                                selected_author = random.choice(authors)
                                selected_author.mail = azure_article_data["emails"][0]
                                selected_author.is_correspondence = True

                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_types[i - 1],
                            "articleDOI": doi,
                            "articleCode": journal_name + f"; {recent_volume}({recent_issue}): "
                                                          f"{article_page_range[0]}-{article_page_range[1]}",
                            "articleYear": datetime.now().year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": article_page_range,
                            "articleTitle": {"TR": article_title_tr,
                                             "ENG": article_title_eng},
                            "articleAbstracts": {"TR": abstract_tr,
                                                 "ENG": abstract_eng},
                            "articleKeywords": {"TR": keywords_tr,
                                                "ENG": keywords_eng},
                            "articleAuthors": Author.author_to_dict(authors) if authors else None,
                            "articleReferences": references if references else None,
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

                        if is_test and i >= 3:
                            return 590
                    except Exception as e:
                        i += 1
                        clear_directory(download_path)
                        tb_str = traceback.format_exc()
                        send_notification(GeneralError(
                            f"Passed one article of - PKP - journal {journal_name} with article number {i}. "
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping PKP journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
