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

with_azure = True
with_adobe = True
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
    return final_article_data


def pkp_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
            i += 1
            driver.get(check_url(start_page_url))
            time.sleep(3)
            try:
                article_issues_element = driver.find_element(By.CLASS_NAME, "issues_archive")
                if "eurjther" in start_page_url:
                    elements = driver.find_element(By.CLASS_NAME, "issues_archive").find_elements(By.TAG_NAME, "li")
                    recent_vol_issue_text = elements[2].find_element(By.CLASS_NAME, "title").text
                    volume_link = elements[2].find_element(By.CLASS_NAME, "title").get_attribute("href")
                elif "natprobiotech" in start_page_url:
                    elements = driver.find_element(By.CLASS_NAME, "issues_archive").find_elements(By.TAG_NAME, "li")
                    recent_vol_issue_text = elements[-1].find_element(By.CLASS_NAME, "title").text
                    volume_link = elements[-1].find_element(By.CLASS_NAME, "title").get_attribute("href")
                else:
                    if "beslenmevediyetdergisi" in start_page_url or "actamedica" in start_page_url:
                        recent_vol_issue_text = article_issues_element.find_element(By.TAG_NAME,
                                                                                    "h2").text
                        volume_link = article_issues_element.find_element(By.TAG_NAME,
                                                                          "h2").find_element(By.TAG_NAME, "a").get_attribute("href")
                    else:
                        recent_vol_issue_text = article_issues_element.find_element(By.CLASS_NAME, "series").text
                        volume_link = article_issues_element.find_element(By.CLASS_NAME, "title").get_attribute("href") \
                            if "press" not in article_issues_element.find_element(By.CLASS_NAME, "title").text else None

                numbers = re.findall(r'\d+', recent_vol_issue_text)
                numbers = [int(i) for i in numbers]
                recent_volume, recent_issue = numbers[:2]

                if not volume_link:
                    raise GeneralError(f"No volume_link found for the journal {journal_name}")
            except Exception as e:
                raise e
            print("vol link found")
            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
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
                            page_ranges.append(section_element.find_element(By.CLASS_NAME, "pages").text.strip())
                            article_types.append(
                                identify_article_type(article_section.find_element(By.TAG_NAME, "h2").text, 0))
                except Exception as e:
                    raise e
                print("url gezmeye başladık")
                for url in article_urls:
                    try:
                        driver.get(url)
                        time.sleep(2)
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
                                author.all_speciality = author_element.find_element(By.CLASS_NAME,
                                                                                    "affiliation").text.strip()
                                authors.append(author)
                        except Exception as e:
                            raise e

                        # References
                        references = list()
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

                        # DOI
                        try:
                            doi = article_element.find_element(By.CSS_SELECTOR, ".item.doi").find_element(By.CLASS_NAME,
                                                                                                          "value").text.strip()
                            doi = doi[doi.index("/10.") + 1:]
                        except Exception:
                            doi = ""

                        # Download Link
                        download_link = article_element.find_element(By.CSS_SELECTOR,
                                                                     ".obj_galley_link.pdf").get_attribute("href")
                        # Download, crop and send to Azure Form Recognizer Endpoint
                        download_link = download_link.replace("view", "download")
                        if download_link:
                            driver.get(download_link)
                            if check_download_finish(download_path):
                                file_name = get_recently_downloaded_file_name(download_path)
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
                            print("çift dil")
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
                                keywords = ""

                        # Page range
                        article_page_range = [int(page_ranges[i - 1].split('-')[0].strip()),
                                              int(page_ranges[i - 1].split('-')[1].strip())]

                        if not references and download_link:
                            # Send PDF to Adobe and format response
                            if with_adobe:
                                adobe_cropped = split_in_half(file_name)
                                adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                                references = adobe_references

                        # Get Azure Data
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

                        abbreviation = ""
                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_types[i - 1],
                            "articleDOI": doi,
                            "articleCode": abbreviation if abbreviation else "",
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
                            "articleAuthors": Author.author_to_dict(authors) if authors else [],
                            "articleReferences": references if references else []}
                        final_article_data = populate_with_azure_data(final_article_data, azure_article_data)
                        pprint.pprint(final_article_data)
                        gir = input("devam mı?")
                        if gir == "Y":
                            file_path = r"C:\Users\emine\OneDrive\Masaüstü" + rf"\{file_reference}.json"
                            json_data = json.dumps(final_article_data, ensure_ascii=False, indent=4)
                            with open(file_path, "w", encoding="utf-8") as file:
                                file.write(json_data)
                                print("yazdı")
                            time.sleep(10)
                            import requests
                            # The URL endpoint
                            url = "http://178.62.217.122:8080/article/store"

                            # The request headers
                            headers = {
                                "authorization": "t0U/A2dhjvWuMKkTabbp5IOkXXE2mpfpquMixFFUlTpkwJuOIU93CY=4ftz20-/jUxuxBxW7nqtgWpNf7bJUck6pqGr7=0ZTwA0je6ryUsvYieT?AlPo75TrLiRi0ZBeB/ySwZLfzfB=vjUd4PNx7uAfn?mJ0nL",
                            }

                            # Your dictionary
                            my_dict = final_article_data
                            # Convert the dictionary to a JSON string
                            body = json.dumps(my_dict, ensure_ascii=False)

                            # Encode the payload using UTF-8
                            encoded_payload = {key: value.encode('utf-8') if isinstance(value, str) else value for
                                               key, value in body.items()}

                            # Make the POST request
                            response = requests.post(url, headers=headers, data=encoded_payload)

                            # Print the response
                            print(response.json())



                        if json_two_articles:
                            file_path = "/home/emin/Desktop/col_m9_jsons/" + f"{file_reference}.json"
                            json_data = json.dumps(final_article_data, ensure_ascii=False, indent=4)
                            with open(file_path, "w") as file:
                                file.write(json_data)
                            if i == 3:
                                break
                        # Send data to Client API
                        # TODO send pkp data
                        clear_directory(download_path)
                        return 550
                    except Exception as e:
                        clear_directory(download_path)
                        tb_str = traceback.format_exc()
                        send_notification(GeneralError(
                            f"Passed one article of pkp journal {journal_name} with article number {i}. Error encountered was: {e}. Traceback: {tb_str}"))
                        continue

                    create_logs(True, get_logs_path(parent_type, file_reference))
                    # Update the most recently scanned issue according to the journal type
                    update_scanned_issues(recent_volume, recent_issue,
                                          get_logs_path(parent_type, file_reference))
                    time.sleep(15)
                    return timeit.default_timer() - start_time
            else:
                log_already_scanned(get_logs_path(parent_type, file_reference))
                return timeit.default_timer() - start_time

    except Exception as e:
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping pkp journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return timeit.default_timer() - start_time


if __name__ == "__main__":
    pkp_scraper("foo", "https://natprobiotech.com/index.php/natprobiotech/issue/archive", 2, 3, 4, 5)
"""         
Derleme
Özgün Araştırma
Olgu Sunumu
Tam PDF
Editörden
Editöre Mektup

Message from the Editor-in-Chief
Review
Original Article
Case Report
research
Original Investigation
Interesting Image
Clinical Investigation
Kitap Tanıtımı
"""