# Python libraries
import glob
import pprint
import time
import timeit
import re
import os
import traceback
from datetime import datetime
import json
# Local imports
from classes.author import Author
from common.errors import DownloadError, ParseError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, \
    abstract_formatter, get_correspondance_name
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
from common.services.adobe.adobe_helper import AdobeHelper
from common.errors import GeneralError
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.services.tk_api.tk_service import TKServiceWorker
from common.services.send_notification import send_notification
from common.services.azure.azure_helper import AzureHelper
# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
# Scraper body chunks
from common.helpers.methods.scraper_body_components import dergipark_components

is_test = False


def get_downloads_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    downloads_path = os.path.join(parent_directory_path, "downloads_n_logs",
                                  "dergipark_manual", parent_type,
                                  file_reference, "downloads")
    return downloads_path


def get_logs_path(parent_type: str, file_reference: str) -> str:
    current_file_path = os.path.realpath(__file__)
    parent_directory_path = os.path.dirname(os.path.dirname(current_file_path))
    logs_path = os.path.join(parent_directory_path, "downloads_n_logs",
                             "dergipark_manual", parent_type,
                             file_reference, "logs")
    return logs_path


def log_already_scanned(path_: str):
    """
    This function will create a log file for the already scanned issues.
    :param path_: PATH value of the logs file
    :return: None
    """
    try:
        logs_path = os.path.join(path_, "logs.json")
        with open(logs_path, 'r') as logs_file:
            old_data = json.loads(logs_file.read())
        new_data = old_data.append({'timeOfTrial': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                                    'attemptStatus': 'Already Scanned - No Action Needed'})
        with open(logs_path, 'w') as logs_file:
            logs_file.write(json.dumps(new_data, indent=4))
    except Exception as e:
        send_notification(GeneralError(
            f"Already scanned issue log creation error for Dergipark journal with path = {path_}. Error: {e}"))


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


def check_scan_status(**kwargs):
    try:
        return is_issue_scanned(kwargs["vol"], kwargs["issue"], kwargs["logs_path"])
    except Exception as e:
        send_notification(
            GeneralError(f"Error encountered while checking issue scan status for dergi_platformu journal "
                         f"with path = {kwargs['logs_path']}, (check_scan_status, dergi_platformu_scraper.py). Error: {e}"))
        raise e


def update_scanned_articles(doi=None, url=None, is_doi=True, path_="") -> bool:
    """

    :param doi: Unique DOI of the article
    :param url: URL of the article
    :param is_doi: If True, then the function will update the DOI records, and conversely, URL logs if passed False.
    :param path_: PATH value of logs file
    :return: Returns True if updating was successful
    """
    if is_doi:
        scanned_articles_path = os.path.join(path_, "scanned_article_dois.json")
        try:
            json_file = open(scanned_articles_path, encoding='utf-8')
            scanned_articles_list = json.load(json_file)
            json_file.close()

            if doi in scanned_articles_list:
                return False
            else:
                scanned_articles_list.append(doi)
                with open(scanned_articles_path, 'w') as json_file:
                    json_file.write(json.dumps(scanned_articles_list, indent=4))

                return True

        except FileNotFoundError:
            send_notification(GeneralError("Could not update the scanned article doi records!"))
            return False

    else:
        try:
            scanned_articles_path = os.path.join(path_, "scanned_article_urls.json")
            json_file = open(scanned_articles_path, encoding='utf-8')
            scanned_articles_list = json.load(json_file)
            json_file.close()

            if url in scanned_articles_list:
                return False
            else:
                scanned_articles_list.append(url)
                with open(scanned_articles_path, 'w') as json_file:
                    json_file.write(json.dumps(scanned_articles_list, indent=4))
                return True

        except FileNotFoundError:
            send_notification(GeneralError("Could not update the scanned article doi records!"))
            return False


def update_scanned_issues(vol_num: int, issue_num: int, path_: str, is_tk_no_ref=False, issue_text=None) -> bool:
    """
    Logs path will be passed to the method
    :param issue_text: The bulk text if the journal is a TK no ref journal (eg: (23.03.2023))
    :param is_tk_no_ref: Is journal a TK no ref journal
    :param vol_num: Volume number passed to the function
    :param issue_num: Issue number passed to the function
    :param path_: absolute path of the logs file in logs_n_downloads directory
    :return: Returns True if updating was successful
    """
    try:
        scanned_issues_path = os.path.join(path_, "latest_scanned_issue.json")
        if not is_tk_no_ref:
            last_scanned_items = {"lastScannedVolume": vol_num,
                                  "lastScannedIssue": issue_num,
                                  "lastEdited": datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                                  }

            try:
                with open(scanned_issues_path, 'w') as json_file:
                    json_file.write(json.dumps(last_scanned_items, indent=4))

                return True
            except FileNotFoundError:
                send_notification(GeneralError("Could not update the issue records!"))
                return False
        else:
            last_scanned_items = {"lastScannedText": issue_text.strip(),
                                  "lastEdited": datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                                  }

            try:
                with open(scanned_issues_path, 'w') as json_file:
                    json_file.write(json.dumps(last_scanned_items, indent=4))

                return True
            except FileNotFoundError:
                send_notification(GeneralError("Could not update the issue records!"))
                return False
    except Exception as e:
        send_notification(GeneralError("Could not update the issue records!"))
        raise e


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
                old_data = json.loads(logs_file.read())
        new_data = old_data.append({'timeOfTrial': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                                    'attemptStatus': "Scraping was successful" if was_successful else "Scraping failed"})
        with open(logs_file_path, 'w') as logs_file:
            logs_file.write(json.dumps(new_data, indent=4))

    except Exception as e:
        send_notification(GeneralError('Error encountered while updating Dergipark journal logs file with '
                                       'path = {path_}. Error encountered: {e}'.format(e=e, path_=path_)))


def dergipark_scraper(journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference):
    """
    :param journal_name: The name of the journal as listed in Atıf Dizini
    :param start_page_url: Dergipark startpage
    :param pages_to_send: Number of pages to crop and send, either 1 or 2
    :param pdf_scrape_type: "A_DRG & R" or "A_DRG"
    :param parent_type: Parent folder's name
    :param file_reference: The trimmed and encoded file name for saving the downloads and JSONs
    :return: Returns number of seconds took the scraper to finish
    """
    # Webdriver options
    # Eager option shortens the load time. Always download the pdfs and does not display them.
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
            try:
                dergipark_components.get_to_the_page(driver, start_page_url, journal_name)

                latest_publication_element = dergipark_components.get_latest_data(driver, journal_name)

                temp_txt = latest_publication_element.text

                recent_volume = int(temp_txt[temp_txt.index(":") + 1:temp_txt.index("Sayı")].strip()) \
                    if (not "igusabder" in start_page_url and not "pub/isad" in start_page_url and not "pub/aeskd" in start_page_url) \
                    else int(temp_txt.split()[0])
                try:
                    recent_issue = int(temp_txt.split()[-1])
                except:
                    recent_issue = int(re.findall(r'\d+', temp_txt)[-1])
            except Exception as e:
                raise GeneralError(f"A problem encountered while retrieving the volume or issue data of Dergipark "
                                   f"journal named {journal_name}. Error encountered was: {e}")

            is_issue_scanned = check_scan_status(logs_path=get_logs_path(parent_type, file_reference),
                                                 vol=recent_volume, issue=recent_issue, pdf_scrape_type=pdf_scrape_type)

            # START DOWNLOADS IF ISSUE IS NOT SCANNED
            if not is_issue_scanned:
                if is_test:
                    update_scanned_issues(recent_volume, recent_issue,
                                          get_logs_path(parent_type, file_reference))
                article_urls = list()
                dergipark_components.go_to_issue_page(driver, latest_publication_element, journal_name, recent_volume,
                                                      recent_issue)

                issue_year = dergipark_components.scrape_year_information(driver)

                # Get all elements
                article_elements = dergipark_components.scrape_article_elements(driver, journal_name, recent_volume,
                                                                                recent_issue)

                # Add URLs to article URLs list
                dergipark_components.scrape_article_urls(driver, article_elements, article_urls, journal_name,
                                                         recent_volume,
                                                         recent_issue)

                # GET TO THE ARTICLE PAGE AND TRY TO DOWNLOAD AND PARSE THE ARTICLE PDFs
                for article_url in article_urls:
                    with_adobe, with_azure = True, True
                    if article_url.endswith("/"):
                        article_url = article_url[:-1]
                    driver.get(article_url)
                    time.sleep(5)

                    try:
                        dergipark_references = []
                        keywords_tr = []
                        keywords_eng = []
                        abstract_tr = None
                        abstract_eng = None
                        article_vol = recent_volume
                        article_issue = recent_issue
                        article_year = issue_year

                        # DOWNLOAD ARTICLE PDF
                        try:
                            # PDF LINK THAT WHEN DRIVER GETS THERE THE DOWNLOAD STARTS
                            driver.get(driver.find_element
                                       (By.CSS_SELECTOR,
                                        'a.btn.btn-sm.float-left.article-tool.pdf.d-flex.align-items-center')
                                       .get_attribute('href'))
                            pdf_to_download_available = True
                        except Exception as e:
                            pdf_to_download_available = False
                            if pdf_scrape_type == "A_DRG & R":
                                pass
                            else:
                                raise GeneralError(f"Download error with {journal_name}, article number {i}, "
                                                   f"article URL: {article_url}. Error encountered was: {e}")

                        try:
                            article_type = dergipark_components.define_article_type(driver)
                            if article_type == "Diğer" or article_type == "Editoryal":
                                i += 1
                                continue
                        except Exception:
                            article_type = "ORİJİNAL ARAŞTIRMA"

                        try:
                            article_page_range = dergipark_components.get_page_range(driver)
                        except Exception as e:
                            article_page_range = [0, 1]
                            send_notification(GeneralError(f"No page range found for Dergipark Journal '{journal_name}'"
                                                           f" and article number {i}. Article URL: {article_url}."
                                                           f" Error encountered: {e}"))

                        language_tabs = dergipark_components.get_language_tabs(driver)
                        article_lang_num = len(language_tabs)

                        adobe_references, location_header = None, None
                        if check_download_finish(download_path):
                            # Formatted name will be saved to the variable and the PDF name is already formatted
                            # formatted_name = format_file_name(download_path,
                            #                                   journal_name
                            #                                   + ' '
                            #                                   + str(recent_volume)
                            #                                   + str(recent_issue)
                            #                                   + str(i))

                            file_name = get_recently_downloaded_file_name(download_path, journal_name, article_url)
                            if with_azure:
                                first_pages_cropped_pdf = crop_pages(file_name, pages_to_send)
                                location_header = AzureHelper.analyse_pdf(
                                    first_pages_cropped_pdf, is_tk=False)  # Location header is the response address of Azure API
                                if not location_header:
                                    with_azure = False
                            if with_adobe and pdf_scrape_type.strip() != "A_DRG & R":
                                adobe_pdf_path = split_in_half(file_name)
                                adobe_zip_path = AdobeHelper.analyse_pdf(adobe_pdf_path, download_path)
                                adobe_references = AdobeHelper.get_analysis_results(adobe_zip_path)
                        else:
                            with_adobe, with_azure = False, False
                        # So far, the article has been downloaded if possible, and the name of the file is reformatted
                        # Afterwards the pdf is sent for analysis. In the later stages of the code the response will be fetched.

                        if article_lang_num == 1:
                            if not "bingolsaglik" in start_page_url:
                                article_lang = dergipark_components.define_article_language(driver)
                            else:
                                article_lang = "TR"

                            article_title_elements, keywords_elements, abstract_elements, button = \
                                dergipark_components.get_single_lang_article_elements(driver)
                            if not isinstance(button, int):
                                button.click()
                            time.sleep(0.5)
                            try:
                                reference_list_elements = dergipark_components.get_reference_elements(driver)
                            except:
                                i += 1
                                clear_directory(download_path)
                                continue

                            for reference_element in reference_list_elements:
                                if reference_element.find_elements(By.TAG_NAME, 'li')[0].text:
                                    ref_count = 1
                                    for element in reference_element.find_elements(By.TAG_NAME, 'li'):
                                        if ref_count == 1:
                                            dergipark_references.append(
                                                reference_formatter(element.get_attribute('innerText'), is_first=True,
                                                                    count=ref_count))
                                        else:
                                            dergipark_references.append(
                                                reference_formatter(element.get_attribute('innerText'), is_first=False,
                                                                    count=ref_count))
                                        ref_count += 1

                            if article_lang == "TR":
                                article_title_eng, abstract_eng, keywords_eng = "", "", []
                                for element in article_title_elements:
                                    if element.text:
                                        article_title_tr = element.text.strip()
                                for element in abstract_elements:
                                    if element.text:
                                        abstract_tr = abstract_formatter(element.find_element(By.TAG_NAME, 'p').text,
                                                                         "tr")
                                for element in keywords_elements:
                                    if element.text:
                                        for keyword in element.find_element(By.TAG_NAME, 'p').text.split(','):
                                            if keyword.strip() and keyword.strip() not in keywords_tr:
                                                keywords_tr.append(keyword.strip())
                            else:
                                article_title_tr, abstract_tr, keywords_tr = "", "", []
                                for element in article_title_elements:
                                    if element.text:
                                        article_title_eng = element.text.strip()
                                for element in abstract_elements:
                                    if element.text:
                                        abstract_eng = abstract_formatter(element.find_element(By.TAG_NAME, 'p').text,
                                                                          "eng")
                                for element in keywords_elements:
                                    if element.text:
                                        for keyword in element.find_element(By.TAG_NAME, 'p').text.split(','):
                                            if keyword.strip() and keyword.strip() not in keywords_eng:
                                                keywords_eng.append(keyword.strip())

                        # MULTIPLE LANGUAGE ARTICLES
                        elif article_lang_num == 2:
                            tr_article_element, article_title_tr, abstract_tr = dergipark_components.get_turkish_data(
                                driver, language_tabs)

                            try:
                                keywords_element = dergipark_components.get_multiple_lang_article_keywords(
                                    tr_article_element)
                                if not isinstance(keywords_element, str):
                                    for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute(
                                            'innerText').strip().split(','):
                                        if keyword.strip() and keyword.strip() not in keywords_tr:
                                            keywords_tr.append(keyword.strip())
                                    keywords_tr[-1] = re.sub(r'\.', '', keywords_tr[-1])
                                else:
                                    keywords_tr = []
                            except Exception as e:
                                send_notification(ParseError(
                                    f"Could not scrape keywords of journal {journal_name} with article num {i}."
                                    f"Article URL: {article_url}. Error encountered: {e}"))
                                raise e

                            # GO TO THE ENGLISH TAB
                            language_tabs[1].click()
                            time.sleep(0.7)

                            eng_article_element, article_title_eng, abstract_eng_element = dergipark_components.get_english_data(
                                driver)

                            for part in abstract_eng_element:
                                if part.get_attribute('innerText'):
                                    abstract_eng = abstract_formatter(part.get_attribute('innerText'), "eng")
                            keywords_element = dergipark_components.get_multiple_lang_article_keywords(
                                eng_article_element)

                            if not isinstance(keywords_element, str):
                                for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute(
                                        'innerText').strip().split(','):
                                    if keyword.strip():
                                        keywords_eng.append(keyword.strip())
                                keywords_eng[-1] = re.sub(r'\.', '', keywords_eng[-1])
                            else:
                                keywords_eng = []

                            try:
                                button = driver.find_element(By.XPATH, '//*[@id="show-reference"]')
                                button.click()
                            except:
                                pass
                            time.sleep(0.5)
                            try:
                                reference_list_elements = dergipark_components.get_multiple_lang_article_refs(
                                    eng_article_element)
                            except:
                                i += 1
                                clear_directory(download_path)
                                continue

                            ref_count = 1
                            for reference_element in reference_list_elements:
                                try:
                                    ref_text = reference_element.get_attribute('innerText')
                                    if ref_count == 1:
                                        dergipark_references.append(reference_formatter(ref_text, is_first=True,
                                                                                        count=ref_count))
                                    else:
                                        dergipark_references.append(reference_formatter(ref_text, is_first=False,
                                                                                        count=ref_count))
                                except Exception:
                                    pass
                                ref_count += 1

                        authors = list()
                        author_elements = dergipark_components.get_author_elements(driver)
                        for author_element in author_elements:
                            authors.append(author_converter(author_element.get_attribute('innerText'),
                                                            author_element.get_attribute('innerHTML')))
                        correspondance_name = get_correspondance_name(authors)
                        try:
                            article_doi = dergipark_components.get_doi(driver)
                            article_doi = article_doi[article_doi.index("org/") + 4:]
                        except Exception as e:
                            article_doi = None

                        if pdf_to_download_available:
                            # CHECK IF THE DOWNLOAD HAS BEEN FINISHED
                            if not check_download_finish(download_path):
                                send_notification(DownloadError(f"Download was not finished in time, "
                                                                f"{journal_name, recent_volume, recent_issue},"
                                                                f" article num {i}."))

                        # GET RESPONSE BODY OF THE AZURE RESPONSE
                        azure_article_data = None
                        if with_azure and location_header:
                            azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                            azure_data = azure_response_dictionary["Data"]
                            # Format Azure Response and get a dict
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data,
                                                                                       correspondance_name)
                        # So far both the Azure data and the data scraped from Dergipark are constructed
                        # Additionally, if needed, the references data is fetched from Adobe
                        # At this point the data that will be sent to the API will be finalized
                        # Both data will be compared and the available ones will be selected from both data
                        # Additionally the references will be added if fetched from Adobe
                        # Construct Final Data Dict
                        article_code = f"{journal_name} {article_year};{article_vol}({article_issue})" \
                                       f":{article_page_range[0]}-{article_page_range[1]}"

                        final_article_data = {
                            "journalName": f"{journal_name}",
                            "articleType": article_type if article_type else None,
                            "articleDOI": article_doi if article_doi else None,
                            "articleCode": article_code if article_code else None,
                            "articleYear": article_year,
                            "articleVolume": recent_volume,
                            "articleIssue": recent_issue,
                            "articlePageRange": article_page_range,
                            "articleTitle": {"TR": article_title_tr if article_title_tr else None,
                                             "ENG": article_title_eng if article_title_eng else None},
                            "articleAbstracts": {"TR": abstract_tr if abstract_tr else None,
                                                 "ENG": abstract_eng if abstract_eng else None},
                            "articleKeywords": {"TR": keywords_tr if keywords_tr else None,
                                                "ENG": keywords_eng if keywords_eng else None},
                            "articleAuthors": Author.author_to_dict(authors) if authors else None,
                            "articleReferences": None,
                            "articleURL": article_url,
                            "temporaryPDF": ""}

                        if dergipark_references:
                            final_article_data["articleReferences"] = dergipark_references
                        elif with_adobe and adobe_references:
                            final_article_data["articleReferences"] = adobe_references

                        if azure_article_data:
                            if azure_article_data.get("article_keywords", None):
                                if azure_article_data["article_keywords"].get("tr", None) and not final_article_data["articleKeywords"]["TR"]:
                                    final_article_data["articleKeywords"]["TR"] = \
                                        azure_article_data["article_keywords"]["tr"]
                                if azure_article_data["article_keywords"].get("eng", None) and not final_article_data["articleKeywords"]["ENG"]:
                                    final_article_data["articleKeywords"]["ENG"] = \
                                        azure_article_data["article_keywords"]["eng"]
                            if azure_article_data.get("article_authors", None):
                                final_article_data["articleAuthors"] = azure_article_data["article_authors"]
                            if not final_article_data["articleDOI"] and with_azure:
                                if azure_article_data.get("doi", None):
                                    final_article_data["articleDOI"] = azure_article_data["doi"].strip()

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
                            f"Passed one article of - DERGİPARK - journal {journal_name} with article number {i}."
                            f" Error encountered was: {e}. Article URL is: {article_url}. Traceback: {tb_str}"))
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
        send_notification(
            GeneralError(f"An error encountered and caught by outer catch while scraping Dergipark journal "
                         f"'{journal_name}' with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return 590 if is_test else timeit.default_timer() - start_time
