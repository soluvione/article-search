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
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

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
                             "sayi_sayfalar_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "sayi_sayfalar_manual", parent_type,
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
            GeneralError(f"Error encountered while updating sayi_sayfalar journal logs file with path = {path_}. "
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
                f"Already scanned issue log creation error for sayi_sayfalar journal with path = {path_}. Error: {e}"))


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for sayi_sayfalar journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, sayi_sayfalar_scraper.py). Error: {e}"))
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
    return final_article_data


def sayi_sayfalar_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
    # Webdriver options
    # Eager option shortens the load time. Driver also always downloads the pdfs and does not display them
    options = Options()
    options.page_load_strategy = 'eager'
    download_path = get_downloads_path(parent_type, file_reference)
    prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--disable-notifications")
    options.add_argument('--ignore-certificate-errors')
    # options.add_argument("--headless")  # This line enables headless mode
    service = ChromeService(executable_path=ChromeDriverManager().install())

    # Set start time
    start_time = timeit.default_timer()
    i = 0  # Will be used to distinguish article numbers

    try:
        with (webdriver.Chrome(service=service, options=options) as driver):
            driver.get(check_url(start_page_url))
            time.sleep(3)
            try:
                close_button = driver.find_element(By.XPATH, '//*[@id="myModal2"]/div[2]/div/div[3]/button')
                close_button.click()
                time.sleep(2)
            except Exception:
                pass

            try:  # Salak Behçet Uz dergisinde pop-up çıkıyor her sayfada
                driver.find_element(By.CSS_SELECTOR, 'button[class="confirm"]').click()
            except:
                pass

            try:
                try:
                    main_element = driver.find_element(By.XPATH, '//*[@id="ContentPlaceHolder1_lblContent"]/table')
                except:
                    try:
                        main_element = driver.find_element(By.XPATH,
                                                           '//*[@id="ContentPlaceHolder1_ContentPlaceHolder1_lblContent"]/table')
                    except:
                        main_element = driver.find_element(By.XPATH, '//*[@id="table10"]/tbody/tr/td/table')

                child_element = main_element.find_elements(By.TAG_NAME, 'tr')[2].find_element(By.CLASS_NAME, 'td_parent').find_element(By.TAG_NAME, 'tbody')
                issue_link = child_element.find_elements(By.TAG_NAME, 'a')[-1].get_attribute('href')
                numbers = [int(number) for number in re.findall('\d+', child_element.text)]
                # Volume, Issue and Year
                recent_volume = numbers[0]
                pattern = r"(: \d+)"
                recent_issue = int(re.findall(pattern, child_element.text)[-1][-1])
                article_year = numbers[1]
            except Exception as e:
                raise GeneralError(f"An error occured while retrieving the vol-issue-year data of sayi_sayfalar journal"
                                   f" {journal_name}. Error encountered: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)
            if not is_issue_scanned:
                driver.get(issue_link)
                try:  # Salak Behçet Uz dergisinde pop-up çıkıyor her sayfada
                    driver.find_element(By.CSS_SELECTOR, 'button[class="confirm"]').click()
                except:
                    pass
                article_list = driver.find_element(By.CSS_SELECTOR, "table[cellpadding='4']")
                hrefs = [item.get_attribute('href') for item in article_list.find_elements(By.TAG_NAME, 'a')
                         if ("Makale" in item.text or "Abstract" in item.text)]

                if not hrefs:
                    raise GeneralError(f'No URLs scraped from sayi_sayfalar journal with name: {journal_name}')

                for article_url in hrefs:
                    with_adobe, with_azure = True, True
                    if "showabs" in article_url:
                        continue
                    driver.get(article_url)
                    try:  # Salak Behçet Uz dergisinde pop-up çıkıyor her sayfada
                        driver.find_element(By.CSS_SELECTOR, 'button[class="confirm"]').click()
                    except:
                        pass
                    try:
                        try:
                            article_data_body = driver.find_element(By.XPATH,
                                                                    '//*[@id="ContentPlaceHolder1_lblContent"]/table')
                        except:
                            article_data_body = driver.find_element(By.XPATH,
                                                                    '//*[@id="table10"]/tbody/tr/td/table')

                        try:
                            download_link = driver.find_element(By.XPATH,
                                                            '//*[@id="ContentPlaceHolder1_lblContent"]/table/tbody'
                                                            '/tr[3]/td[2]/table[1]').find_element(By.CSS_SELECTOR,
                                                                                                  'a[target="_blank"]'
                                                                                                  ).get_attribute('href')
                        except:
                            try:
                                download_link = driver.find_element(By.XPATH,
                                                                '//*[@id="table10"]/tbody/tr/td/table/tbody/tr[3]/td[2]/table/tbody/tr[2]/td/a[1]').get_attribute('href')
                            except:
                                download_link = None


                        references = None
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
                                if with_adobe:
                                    adobe_cropped = split_in_half(file_name)
                                    adobe_response = AdobeHelper.analyse_pdf(adobe_cropped, download_path)
                                    adobe_references = AdobeHelper.get_analysis_results(adobe_response)
                                    references = adobe_references
                            else:
                                with_adobe, with_azure = False, False

                        # Abbreviation and DOI
                        try:
                            abbv_doi_element = driver.find_element(By.CSS_SELECTOR, 'td.tool_j')
                            article_code = abbv_doi_element.text.strip().split('.')[0].strip()
                            if not article_code:
                                article_code = None
                            article_doi = abbv_doi_element.text.split("DOI:")[-1].strip()
                            abbreviation = article_code
                        except Exception as e:
                            abbreviation = ""
                            send_notification(GeneralError(
                                f"Error while getting sayi_sayfalar abbreviation and DOI of the article: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))

                        # Page range
                        try:
                            article_page_range = [int(number.strip()) for number in abbv_doi_element.text[
                                                                            abbv_doi_element.text.index(
                                                                                ':') + 1: abbv_doi_element.text.index(
                                                                                '|')].split('-')]
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting sayi_sayfalar page range data of the article: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))

                        # Language Order
                        # Here we are designating the order in which abstracts etc. are listed
                        try:
                            h2_elements = article_data_body.find_elements(By.TAG_NAME, "h2")
                            first_language = driver.find_element(By.CSS_SELECTOR,
                                                                 'meta[name="citation_language"]').get_attribute(
                                'content')
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting sayi_sayfalar language order of the article: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))

                        # Authors
                        try:
                            authors_element = article_data_body.find_element(By.CLASS_NAME, "JAgAuthors")
                            authors_bulk_text = authors_element.text
                            correspondence_name = authors_element.find_element(By.TAG_NAME, "u").text
                            authors_list = [author_name.strip() for author_name in authors_bulk_text.split(",")]
                            specialities_element = article_data_body.find_element(By.CLASS_NAME, "JAgAffiliations")
                            html_string = specialities_element.get_attribute('innerHTML')

                            # parse the HTML with BeautifulSoup
                            soup = BeautifulSoup(html_string, 'html.parser')

                            # remove the <sup> elements
                            for sup in soup.find_all('sup'):
                                sup.decompose()

                            # separate affiliations by <br> tags and get the text of each affiliation
                            affiliations = [str(affiliation).strip() for affiliation in soup.stripped_strings]
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting sayi_sayfalar article authors' data of journal: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))
                            raise e

                        # Construct Authors List
                        author_list = list()
                        for author_name in authors_list:
                            author = Author()
                            author.name = author_name[:-1] if author_name[-1].isdigit() else author_name
                            author.is_correspondence = True if fuzz.ratio(author.name.lower(),
                                                                          correspondence_name.lower()) > 80 else False
                            try:
                                author.all_speciality = affiliations[int(author_name[-1]) - 1]
                            except ValueError:
                                author.all_speciality = affiliations[0]
                            author_list.append(author)

                        # Abstracts
                        # If there are two abstracts, the second ones should be gotten from Azure services
                        try:
                            abstracts = [element.text.strip() for element in
                                         article_data_body.find_elements(By.TAG_NAME, "p")]
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting sayi_sayfalar article abstracts data of journal: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))
                            raise e


                        # Get Azure Data
                        if with_azure:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                            azure_data = azure_response_dictionary["Data"]
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data)
                            if len(azure_article_data["emails"]) == 1:
                                for author in author_list:
                                    author.mail = azure_article_data["emails"][0] if author.is_correspondence else None

                        # Keywords
                        # There are 2 kinds of keywords for sayi_sayfalar journals. The one acquired from the meta tagged
                        # elements and the one acquired from the bulk of text
                        try:
                            keywords_element_meta = driver.find_elements(By.CSS_SELECTOR, 'meta[name="keywords"]')
                            # get the content attribute of the meta tag
                            keywords_text = keywords_element_meta[-1].get_attribute("content")
                            keywords_meta = [keyword.strip() for keyword in keywords_text.split(",")]

                            soup = BeautifulSoup(article_data_body.get_attribute("innerHTML"), 'html.parser')

                            if len(h2_elements) == 2:
                                if first_language == "en":
                                    keyword_element = soup.find('b', string='Anahtar Kelimeler:')
                                else:
                                    keyword_element = soup.find('b', string='Keywords:')
                                # Extract the keywords
                                keywords_text = keyword_element.find_next_sibling(string=True)
                                keywords_last_element = [keyword.strip() for keyword in keywords_text.split(',')]
                        except Exception as e:
                            send_notification(GeneralError(
                                f"Error while getting sayi_sayfalar article keywords data of journal: {journal_name}"
                                f" with article num {i}. Error encountered was: {e}"))

                        # Distribute the acquired data in accordance with the number and order of the languages in the
                        # article page
                        number_of_language = len(h2_elements)
                        if number_of_language == 1:
                            if first_language == "en":
                                article_title_eng = h2_elements[0].text.strip()
                                article_title_tr = ""
                                abstract_eng = abstracts[0].strip()
                                abstract_tr = ""
                                keywords_eng = keywords_meta
                                keywords_tr = []
                            else:
                                article_title_eng = ""
                                article_title_tr = h2_elements[0].text
                                abstract_eng = ""
                                abstract_tr = abstracts[0].strip()
                                keywords_eng = []
                                keywords_tr = keywords_meta
                        else:
                            if first_language == "en":
                                article_title_eng = h2_elements[0].text.strip()
                                article_title_tr = h2_elements[1].text.strip()
                                abstract_eng = abstracts[0].strip()
                                abstract_tr = abstracts[1].strip()
                                keywords_eng = keywords_meta
                                keywords_tr = keywords_last_element
                            else:
                                article_title_eng = h2_elements[1].text.strip()
                                article_title_tr = h2_elements[0].text.strip()
                                abstract_eng = abstracts[1].strip()
                                abstract_tr = abstracts[0].strip()
                                keywords_eng = keywords_last_element
                                keywords_tr = keywords_meta

                        # Article Type
                        article_type = "OLGU SUNUMU" if (
                                    "case" in journal_name.lower() or "case" in article_title_eng.lower()
                                    or "olgu" in article_title_tr.lower() or "sunum" in article_title_tr.lower()
                                    or "bulgu" in article_title_tr.lower()) else "ORİJİNAL ARAŞTIRMA"

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
                            f"Passed one article of sayi_sayfalar journal {journal_name} with article number {i}. "
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
        send_notification(GeneralError(f"An error encountered and caught by outer catch while scraping sayi_sayfalar journal "
                                       f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
