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
from common.services.tk_api.tk_service import TKServiceWorker
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
is_test = True

def check_url(url):
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "ended_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "ended_manual", parent_type,
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
            GeneralError(f"Error encountered while updating ended journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for ended journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for ended journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, ended_scraper.py). Error: {e}"))
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


def ended_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
    i = 0  # Will be used to distinguish article numbers
    try:
        with webdriver.Chrome(service=service, options=options) as driver:
            try:
                # ARCHIEVE PAGE TO THE LATEST ISSUE
                driver.get(start_page_url)
                driver.maximize_window()
                time.sleep(1)
                # The archive page has either two styles, list or boxes
                try:
                    col_lg_element = driver.find_element(By.CSS_SELECTOR, ".col-lg-6.col-md-6.col-sm-6.col-xs-12")
                except Exception:
                    col_lg_element = None
                print("ha bura")

                if col_lg_element:
                    year = int(col_lg_element.find_element(By.CLASS_NAME, "panel-heading").text)
                    vol_issue_text = col_lg_element.find_element(By.CLASS_NAME, "list-group-item-archive").text
                    numbers = re.findall(r'\d+', vol_issue_text)
                    numbers = [int(i) for i in numbers]
                    recent_volume, recent_issue = numbers
                    issue_link = col_lg_element.find_element(By.CLASS_NAME, "list-group-item-archive").find_element(
                        By.TAG_NAME, "a") \
                        .get_attribute("href")
                else:
                    try:
                        driver.find_element(By.CSS_SELECTOR, "[data-toggle='collapse']").click()
                    except Exception:
                        pass
                    time.sleep(1)
                    main_element = driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME,
                                                                                             "col-md-12").get_attribute(
                        'outerHTML')
                    soup = BeautifulSoup(main_element, 'html.parser')

                    # Find all 'a' tags
                    a_tags = soup.find_all('a')

                    # Filter out 'a' tags that have no text inside them
                    a_tags_with_text = [tag for tag in a_tags if tag.text.strip() and "supp" not in tag.text.lower()
                                        and "ek" not in tag.text.lower()]
                    first_six_a_tags_with_text = a_tags_with_text[1:7]

                    # Remove 'a' tags that contain 'ek' or 'supp'
                    first_six_a_tags_with_text = [tag for tag in first_six_a_tags_with_text if
                                                  "ek" not in tag.text.lower() and "supp" not in tag.text.lower()]

                    # Remove the first element
                    first_six_a_tags_with_text.pop(0) if first_six_a_tags_with_text[0].text == "2023" or \
                                                         first_six_a_tags_with_text[0].text == "2022" else -1

                    # Identify issue number and issue link
                    recent_issue, issue_link = None, None
                    for i in range(len(first_six_a_tags_with_text)):
                        current_issue = re.findall(r'\d+', first_six_a_tags_with_text[i].text)
                        next_issue = re.findall(r'\d+', first_six_a_tags_with_text[i + 1].text) if i + 1 < len(
                            first_six_a_tags_with_text) else None
                        if int(current_issue[0]) == 2022 or int(next_issue[0]) == 2022:
                            break
                        if current_issue and next_issue and int(current_issue[0]) > int(next_issue[0]):
                            recent_issue = int(current_issue[0])
                            issue_link = urljoin(start_page_url, first_six_a_tags_with_text[i]['href'])
                            break

                        elif current_issue and i + 1 == len(first_six_a_tags_with_text):
                            recent_issue = int(current_issue[0])
                            issue_link = urljoin(start_page_url, first_six_a_tags_with_text[i]['href'])
                            break

                    # Extract year
                    year = int(driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME,
                                                                                         "col-md-12").text.split()[1])
                    print("ha burada")
                    # Year is the volume for these journals
                    recent_volume = year

                if not issue_link:
                    raise GeneralError(f"No volume_link found for the journal {journal_name}")
            except Exception as e:
                raise e
            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                driver.get(issue_link)
                time.sleep(4)
                try:
                    # ISSUE PAGE TO THE ARTICLE PAGE
                    text = driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME, "col-md-12").text
                    try:
                        text = text[text.index("Vol"):]
                    except:
                        text = text[text.index("Cilt"):]
                    recent_volume = int(re.findall(r'\d+', text)[0])
                    soup = BeautifulSoup(
                        driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME,
                                                                                  "col-md-12").get_attribute(
                            "outerHTML"), 'html.parser')

                    # Article titles
                    titles = soup.find_all('a', {'class': 'article_title'})
                    titles_text = [item.get_text() for item in soup.find_all('a', {'class': 'article_title'})]

                    # Article links
                    article_urls = list()
                    for item in titles:
                        article_urls.append(item.get("href", None))
                    if not article_urls:
                        article_links = soup.find_all('a', href=True, class_="btn btn-xs btn-success")

                    if soup.find_all('span', {'style': 'color:#5c5c5c'}):
                        for item in soup.find_all('span', {'style': 'color:#5c5c5c'}):
                            pass

                    else:
                        for item in soup.find_all('a', attrs={'name': True}):
                            parent_element = item.parent
                            parent_text = parent_element.text.strip()
                    elements = soup.select('a[href]:has(span.glyphicon.glyphicon-circle-arrow-right)')

                    # Types array hold the type of the article
                    article_types = []
                    for element in elements:
                        element_text = re.sub(r"[^A-Za-z\s]", "", element.get_text(strip=True))
                        number_of_times = re.findall(r"\d+", element.get_text(strip=True))[0]
                        for i in range(int(number_of_times)):
                            article_types.append(element_text.strip())
                except Exception as e:
                    raise e

                for article_url in article_urls:
                    print("ha buraaaa")
                    try:
                        driver.get(urljoin(start_page_url, article_url))
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

                        # Keywords
                        response = requests.get("https://cts.tgcd.org.tr/abstract.php?id=188")
                        soup = BeautifulSoup(response.content, 'html.parser')
                        meta_tag = soup.find('meta', attrs={'name': 'citation_keywords'})

                        # Check if the tag is found and print the content
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

                        # Download, crop and send to Azure Form Recognizer Endpoint
                        if False:
                            driver.get(download_link)
                            if check_download_finish(download_path):
                                file_name = get_recently_downloaded_file_name(download_path)
                                # Send PDF to Azure and format response
                                if with_azure:
                                    first_pages_cropped_pdf = crop_pages(file_name, pages_to_send)
                                    location_header = AzureHelper.analyse_pdf(
                                        first_pages_cropped_pdf,
                                        is_tk=False)  # Location header is the response address of Azure API

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
                        article_lang = "tr" if "ü" in journal_name or "ğ" in journal_name else "en"
                        abbreviation = ""
                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": identify_article_type(article_types[i - 1], 0),
                            "articleDOI": doi,
                            "articleCode": abbreviation if abbreviation else None,
                            "articleYear": datetime.now().year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": None,
                            "articleTitle": {"TR": re.sub(r'[\t\n]', '', titles_text[i-1]).strip() if article_lang == "tr" else None,
                                             "ENG": re.sub(r'[\t\n]', '', titles_text[i-1]).strip() if article_lang == "en" else None},
                            "articleAbstracts": {"TR": re.sub(r'[\t\n]', '', abstract).strip() if article_lang == "tr" else None,
                                                 "ENG": re.sub(r'[\t\n]', '', abstract).strip() if article_lang == "en" else None},
                            "articleKeywords": {"TR": re.sub(r'[\t\n]', '', keywords) if article_lang == "tr" else None,
                                                "ENG": re.sub(r'[\t\n]', '', keywords) if article_lang == "en" else None},
                            "articleAuthors": Author.author_to_dict(authors) if authors else [],
                            "articleReferences": []}
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
                        i += 1
                        clear_directory(download_path)
                        tb_str = traceback.format_exc()
                        send_notification(GeneralError(
                            f"Passed one article of ended journal {journal_name} with article number {i}. Error encountered was: {e}. Traceback: {tb_str}"))
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping ended journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
