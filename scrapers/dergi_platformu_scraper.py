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
                             "dergi_platformu_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "dergi_platformu_manual", parent_type,
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
            GeneralError(f"Error encountered while updating dergi_platformu journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for dergi_platformu journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for dergi_platformu journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, dergi_platformu_scraper.py). Error: {e}"))
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


def dergi_platformu_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
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
    service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")

    # Set start time
    start_time = timeit.default_timer()
    i = 0  # Will be used to distinguish article numbers

    try:
        with (webdriver.Chrome(service=service, options=options) as driver):
            driver.get(check_url(start_page_url))
            time.sleep(3)
            try:
                archives_element = driver.find_element(By.CSS_SELECTOR, 'div[id="sayilar-menusu"]')
                archives_element.find_element(By.CSS_SELECTOR,
                                              'a[class="card-header menu-title head-color special-border1 px-06 collapsed"]').click()
                time.sleep(2)
                vol_issue_element = driver.find_element(By.CSS_SELECTOR, 'ul.list-group.lg-year')
                try:
                    vol_issue_element = \
                    vol_issue_element.find_elements(By.CSS_SELECTOR, 'li[class^="list-group-item"]')[-1]
                except Exception:
                    pass  # Intentional pass
                numbers = re.findall(r'\d+', vol_issue_element.text)
                recent_volume = int(numbers[0])
                recent_issue = int(numbers[1])
            except Exception as e:
                raise GeneralError(f"Could not retrieve the volume or issue value of dergi_platformu journal "
                                   f"{journal_name}! Error encountered was: {e}.")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                # These will be acquired from the issue page
                article_urls = list()
                types = list()
                article_page_ranges = list()
                dois = list()
                download_links = list()
                trials = 0

                articles_columns_element = driver.find_element(By.CSS_SELECTOR, 'section[id="timeline"]')
                article_elements = articles_columns_element.find_elements(By.CSS_SELECTOR, 'ul[class="timeline"]')
                for article_element in article_elements:
                    try:
                        dois.append(article_element.find_element(By.CSS_SELECTOR, 'a[href^="http://dx.doi."').get_attribute('href').strip())
                        article_urls.append(article_element.find_element(By.CSS_SELECTOR, 'a[target="_blank"]').get_attribute('href'))
                        full_type = article_element.find_element(By.CSS_SELECTOR, 'font[style="background-color: rgba(77, 92, 242, 0.1);padding: 4px;padding-right: 5px;padding-left: 5px;border-radius: 5px;font-weight: 500;"]')
                        types.append(full_type.text.strip())
                        full_title = article_element.find_element(By.CSS_SELECTOR, 'a[target="_blank"]').text
                        article_page_ranges.append([int(number.strip()) for number in re.findall('[0-9]+-[0-9]+', full_title)[0].split('-')])
                        download_links.append(article_element.find_elements(By.CSS_SELECTOR, 'li[class="list-inline-item mr-1"]')[2].find_element(By.TAG_NAME, 'a').get_attribute('href'))
                    except Exception as e:
                        trials += 1
                        if trials > 2:
                            raise e

                # Start scraping from individual article pages
                for article_url in article_urls:
                    with_adobe, with_azure = True, True
                    try:
                        driver.get(article_url)
                        index_of_journal = article_urls.index(article_url)
                        if "target" in start_page_url:
                            title_eng = driver.find_element(By.CSS_SELECTOR, 'h3[id="baslik"]').text.strip()
                            keywords_eng = [keyword.text.strip() for keyword in
                                            driver.find_element(By.CSS_SELECTOR, 'p[id="ing_kelime"]').find_elements(By.TAG_NAME, 'span')]
                            abstract_eng = driver.find_element(By.CSS_SELECTOR, 'section[id="content2"]').text.strip()
                            abstract_eng = abstract_eng[abstract_eng.index("\n"):abstract_eng.index("Keywords")].strip()

                            # No TR input for Target Journal
                            title_tr, abstract_tr, keywords_tr = None, None, None
                        else:
                            language_bar_element = driver.find_element(By.CSS_SELECTOR, 'div[class="tab_container "]')
                            language_bar_element.find_element(By.CSS_SELECTOR, 'label[for="tab1"]').click()
                            time.sleep(3)
                            title_tr = driver.find_element(By.CSS_SELECTOR, 'h3[id="baslik"]').text.strip()
                            abstract_tr = driver.find_element(By.CSS_SELECTOR, 'section[id="content1"]').text.strip()
                            abstract_tr = abstract_tr[abstract_tr.index("\n"):abstract_tr.index("Keywords")].strip()
                            keywords_tr = [keyword.text.strip() for keyword in driver.find_element(By.CSS_SELECTOR, 'p[id="tr_kelime"]').find_elements(By.TAG_NAME, 'span')]

                            language_bar_element.find_element(By.CSS_SELECTOR, 'label[for="tab2"]').click()
                            time.sleep(3)
                            title_eng = driver.find_element(By.CSS_SELECTOR, 'h3[id="baslik"]').text.strip()
                            abstract_eng = driver.find_element(By.CSS_SELECTOR, 'section[id="content2"]').text.strip()
                            abstract_eng = abstract_eng[abstract_eng.index("\n"):abstract_eng.index("Keywords")].strip()
                            keywords_eng = [keyword.text.strip() for keyword in driver.find_element(By.CSS_SELECTOR, 'p[id="ing_kelime"]').find_elements(By.TAG_NAME, 'span')]

                        # References and Download link
                        references = None  # No references available on the pages
                        try:
                            download_link = download_links[index_of_journal]
                        except Exception:
                            download_link = None

                        # DOI
                        try:
                            article_doi = dois[index_of_journal]
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting dergi_platformu abbreviation and DOI of the article: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))

                        # Page range
                        try:
                            article_page_range = article_page_ranges[index_of_journal]
                        except Exception as e:
                            article_page_range = [0, 1]
                            pass

                        # Authors
                        try:
                            authors_names = driver.find_element(By.CSS_SELECTOR, 'p[id="yazar"]').find_elements(By.TAG_NAME,
                                                                                                          'span')
                            authors_names = [author.text.strip() for author in authors_names if len(author.text.strip()) > 5]
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting dergi_platformu article authors' data of journal: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))
                            raise e

                        # Construct Authors List
                        author_list = list()
                        for author_name in authors_names:
                            author = Author()
                            author.name = author_name
                            author.is_correspondence = False
                            author_list.append(author)

                        if download_link:
                            driver.get(download_link)
                            time.sleep(2)
                            driver.find_element(By.CSS_SELECTOR, 'a[class="btn btn-info"]').click()
                            # IMPORTANT!
                            # Dergi platformu journals do not download documents directly!
                            if check_download_finish(download_path):
                                file_name = get_recently_downloaded_file_name(download_path)
                                # Send PDF to Azure and format response
                                if with_azure:
                                    first_pages_cropped_pdf = crop_pages(file_name, pages_to_send)
                                    location_header = AzureHelper.analyse_pdf(
                                        first_pages_cropped_pdf,
                                        is_tk=False)  # Location header is the response address of Azure API
                                if with_adobe:
                                    adobe_cropped = split_in_half(file_name)
                                    adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                    adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                                    references = adobe_references
                            else:
                                with_adobe, with_azure = False, False

                        # Get Azure Data
                        if with_azure and file_name:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                            azure_data = azure_response_dictionary["Data"]
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data)
                            if len(azure_article_data["emails"]) == 1:
                                for author in author_list:
                                    author.mail = azure_article_data["emails"][0] if author.is_correspondence else None

                        # Article Type
                        try:
                            article_type = identify_article_type(types[index_of_journal], 0)
                        except Exception:
                            send_notification(GeneralError(
                                f"Error while getting dergi_platformu article keywords data of journal: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))

                        # Abbreviation
                        if "target" in start_page_url:
                            abbreviation = "Int Target Med J"
                        elif "anatoljhr" in start_page_url:
                            abbreviation = "Anatolian J Health Res"
                        elif "tjdn" in start_page_url:
                            abbreviation = "Turkish Journal of Diabetes Nursing"
                        else:
                            abbreviation = "Turk J Health S"

                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_type,
                            "articleDOI": article_doi,
                            "articleCode": abbreviation + f"; {recent_volume}({recent_issue}): "
                                                          f"{article_page_range[0]}-{article_page_range[1]}",
                            "articleYear": datetime.now().year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": article_page_range,
                            "articleTitle": {"TR": title_tr,
                                             "ENG": title_eng},
                            "articleAbstracts": {"TR": abstract_tr,
                                                 "ENG": abstract_eng},
                            "articleKeywords": {"TR": keywords_tr,
                                                "ENG": keywords_eng},
                            "articleAuthors": Author.author_to_dict(author_list) if author_list else None,
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

                        if is_test and i >= 2:
                            return 590
                    except Exception as e:
                        i += 1
                        clear_directory(download_path)
                        tb_str = traceback.format_exc()
                        send_notification(GeneralError(
                            f"Passed one article of dergi_platformu journal {journal_name} with article number {i}."
                            f" Error encountered was: {e}. Traceback: {tb_str}"))
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping dergi_platformu"
                                       f" journal {journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
