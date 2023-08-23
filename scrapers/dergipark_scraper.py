"""
This is the template scraper that will be used to multiply.
"""
import os
from datetime import datetime
import json
import random
from common.services.adobe.adobe_helper import AdobeHelper
from common.services.send_sms import send_notification, send_example_log
from common.erorrs import GeneralError


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


def dergipark_scraper(journal_name, start_page_url, pages_to_send, pdf_scrape_type, parent_type, file_reference):
    """

    :param journal_name: The name of the journal as listed in Atıf Dizini
    :param start_page_url: Dergipark startpage
    :param pages_to_send: Number of pages to crop and send, either 1 or 2
    :param pdf_scrape_type: "A_DRG & R" or "A_DRG"
    :param parent_type: Parent folder's name
    :param file_reference: The trimmed and encoded file name for saving the downloads and JSONs
    :return:
    """
    # Python libraries
    import time
    import timeit
    import os
    import re
    import json

    import common.helpers.methods.others
    # Local imports
    from classes.author import Author
    from common.erorrs import DownloadError, ParseError, GeneralError
    from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
    from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
    from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter
    from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
        abstract_formatter, get_correspondance_name
    from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
    from common.services.send_sms import send_notification
    from common.services.azure.azure_helper import AzureHelper
    # 3rd Party libraries
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    # Scraper body chunks
    from common.helpers.methods.scraper_body_components import dergipark_components
    try:
        # Webdriver options
        # Eager option shortens the load time. Always download the pdfs and does not display them.
        options = Options()
        options.page_load_strategy = 'eager'
        download_path = get_downloads_path(parent_type, file_reference)
        # download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../downloads') #  This part will be updated according to the journal name path
        prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
        options.add_experimental_option('prefs', prefs)
        options.add_argument("--disable-notifications")
        options.add_argument('--ignore-certificate-errors')
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Metadata about the journal
        # Scrape types has 2 options, either unique (A_UNQ) or Dergipark (A_DRG). PDF scrape types can vary more than that.
        journal_name = journal_name
        pdf_scrape_type = pdf_scrape_type
        pages_to_send = pages_to_send
        start_page_url = start_page_url
        adobe_references = None

        # Set start time
        start_time = timeit.default_timer()
        # GLOBAL VARS
        # For a given journal issue, represents how many journal articles have been scraped successfully.
        num_successfully_scraped = 0
        pdf_to_download_available = False
        # Either contains Article URLs or PDF links of each article element
        article_url_list = []
        article_download_element_list = []

        dergipark_components.get_to_the_page(driver, start_page_url, journal_name)

        latest_publication_element = dergipark_components.get_latest_data(driver, journal_name)

        temp_txt = latest_publication_element.text
        recent_volume = int(temp_txt[temp_txt.index(":") + 1:temp_txt.index("Sayı")].strip())
        recent_issue = int(temp_txt.split()[-1])

        # START DOWNLOADS IF ISSUE IS NOT SCANNED
        if True:
            dergipark_components.go_to_issue_page(driver, latest_publication_element, journal_name, recent_volume,
                                                  recent_issue)

            issue_year = dergipark_components.scrape_year_information(driver)

            # Get all elements
            article_elements = dergipark_components.scrape_article_elements(driver, journal_name, recent_volume,
                                                                            recent_issue)

            # Add URLs to article URLs list
            dergipark_components.scrape_article_urls(driver, article_elements, article_url_list, journal_name,
                                                     recent_volume,
                                                     recent_issue)

            # GET TO THE ARTICLE PAGE AND TRY TO DOWNLOAD AND PARSE THE ARTICLE PDFs
            article_num = 0
            for i in range(3):  # article_url in article_url_list
                with_adobe, with_azure = True, True
                article_url = article_url_list[i]
                article_num += 1
                if article_num > 1:
                    driver.execute_script("window.history.go(-1)")
                    WebDriverWait(driver, timeout=3).until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')))
                if True:
                    try:
                        # ARTICLE VARIABLES SCRAPED FROM DERGIPARK PAGE
                        is_scraped_online = True
                        url = article_url
                        article_type = None
                        article_title_tr = None
                        article_title_eng = None
                        authors = []
                        dergipark_references = []
                        keywords_tr = []
                        keywords_eng = []
                        abstract_tr = None
                        abstract_eng = None
                        doi = None
                        article_page_range = [0, 1]
                        article_lang_num = None
                        article_vol = recent_volume
                        article_issue = recent_issue
                        article_year = issue_year
                        article_code = ""  # Enter the code algorithms specific to the article

                        # GET TO ARTICLE PAGE AND GET ELEMENTS IF POSSIBLE FROM THE UNIQUE ARTICLE PAGE
                        driver.get(article_url)

                        pdf_to_download_available = dergipark_components.download_article_pdf(driver, pdf_scrape_type)

                        article_type = dergipark_components.define_article_type(driver)
                        if article_type == "Diğer" or article_type == "Editoryal":
                            continue

                        article_page_range = dergipark_components.get_page_range(driver)

                        language_tabs = dergipark_components.get_language_tabs(driver)
                        article_lang_num = len(language_tabs)

                        if check_download_finish(download_path):
                            # Formatted name will be saved to the variable and the PDF name is already formatted
                            formatted_name = format_file_name(download_path,
                                                              journal_name
                                                              + ' '
                                                              + str(recent_volume)
                                                              + str(recent_issue)
                                                              + str(article_num))
                            if with_azure:
                                first_pages_cropped_pdf = crop_pages(formatted_name, pages_to_send)
                                location_header = AzureHelper.analyse_pdf(
                                    first_pages_cropped_pdf)  # Location header is the response address of Azure API
                            if with_adobe and pdf_scrape_type != "A_DRG & R":
                                adobe_pdf_path = split_in_half(formatted_name)
                                adobe_zip_path = AdobeHelper.analyse_pdf(adobe_pdf_path, download_path)
                                adobe_references = AdobeHelper.get_analysis_results(adobe_zip_path)
                        else:
                            with_adobe, with_azure = False, False
                        # So far, the article has been downloaded if possible, and the name of the file is reformatted
                        # Afterwards the pdf is sent for analysis. In the later stages of the code the response will be fetched.

                        if article_lang_num == 1:
                            article_lang = dergipark_components.define_article_language(driver)

                            article_title_elements, keywords_elements, abstract_elements, button = \
                                dergipark_components.get_single_lang_article_elements(driver)
                            button.click()
                            time.sleep(0.4)
                            reference_list_elements = dergipark_components.get_reference_elements(driver)

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
                                for element in article_title_elements:
                                    if element.text:
                                        article_title_tr = element.text
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
                                for element in article_title_elements:
                                    if element.text:
                                        article_title_eng = element.text
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

                                for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute(
                                        'innerText').strip().split(','):
                                    if keyword.strip() and keyword.strip() not in keywords_tr:
                                        keywords_tr.append(keyword.strip())
                                keywords_tr[-1] = re.sub(r'\.', '', keywords_tr[-1])
                            except Exception:
                                send_notification(ParseError(
                                    f"Could not scrape keywords of journal {journal_name} with article num {article_num}."))
                                # raise ParseError(f"Could not scrape keywords of journal {journal_name} with article num {article_num}.")
                                pass

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

                            for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute(
                                    'innerText').strip().split(','):
                                if keyword.strip():
                                    keywords_eng.append(keyword.strip())
                            keywords_eng[-1] = re.sub(r'\.', '', keywords_eng[-1])

                            button = driver.find_element(By.XPATH, '//*[@id="show-reference"]')
                            button.click()
                            time.sleep(0.4)
                            reference_list_elements = dergipark_components.get_multiple_lang_article_refs(
                                eng_article_element)
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
                        author_elements = dergipark_components.get_author_elements(driver)
                        for author_element in author_elements:
                            authors.append(author_converter(author_element.get_attribute('innerText'),
                                                            author_element.get_attribute('innerHTML')))
                        correspondance_name = get_correspondance_name(authors)
                        try:
                            doi = dergipark_components.get_doi(driver)
                            doi = doi[doi.index("org/") + 4:]
                        except Exception as e:
                            send_notification(GeneralError(f" {journal_name, recent_volume, recent_issue}"
                                                           f" with article num {article_num} was not successful. DOI error was encountered. The problem encountered was: {e}"))
                    except Exception as e:
                        send_notification(GeneralError(
                            f"Scraping journal elements of Dergipark journal"
                            f" {journal_name, recent_volume, recent_issue}"
                            f" with article num {article_num} was not successful. The problem encountered was: {e}"))
                        is_scraped_online = False
                    if pdf_to_download_available:
                        # CHECK IF THE DOWNLOAD HAS BEEN FINISHED
                        if not check_download_finish(download_path):
                            send_notification(DownloadError(f"Download was not finished in time, "
                                                            f"{journal_name, recent_volume, recent_issue},"
                                                            f" article num {article_num}."))
                            if clear_directory(download_path):
                                continue
                            else:
                                send_notification(GeneralError(f"Downloaded file could not deleted, "
                                                               f"{journal_name, recent_volume, recent_issue},"
                                                               f" article num {article_num}."))

                        if True:
                            # GET RESPONSE BODY OF THE AZURE RESPONSE
                            if with_azure:
                                azure_response_dictionary = AzureHelper.get_analysis_results(location_header, 30)
                                azure_data = azure_response_dictionary["Data"]
                            if True:
                                # Format Azure Response and get a dict
                                azure_article_data = None
                                if with_azure:
                                    azure_article_data = AzureHelper.format_general_azure_data(azure_data,
                                                                                               correspondance_name)
                                article_code = f"{journal_name} {article_year};{article_vol}({article_issue})" \
                                               f":{article_page_range[0]}-{article_page_range[1]}"
                                # So far both the Azure data and the data scraped from Dergipark are constructed
                                # Additionally, if needed, the references data is fetched from Adobe
                                # At this point the data that will be sent to the API will be finalized
                                # Both data will be compared and the available ones will be selected from both data
                                # Additionally the references will be added if fetched from Adobe
                                # Construct Final Data Dict
                                final_article_data = {
                                    "journalName": f"{journal_name}",
                                    "articleType": "",
                                    "articleDOI": "",
                                    "articleCode": article_code,
                                    "articleYear": article_year,
                                    "articleVolume": recent_volume,
                                    "articleIssue": recent_issue,
                                    "articlePageRange": article_page_range,
                                    "articleTitle": {"TR": "", "ENG": ""},
                                    "articleAbstracts": {"TR": "", "ENG": ""},
                                    "articleKeywords": {"TR": [], "ENG": []},
                                    "articleAuthors": [],
                                    "articleReferences": []}
                                if article_type:
                                    final_article_data["articleType"] = article_type

                                if doi:
                                    final_article_data["articleDOI"] = doi
                                elif azure_article_data:
                                    if azure_article_data.get("doi", None):
                                        final_article_data["articleDOI"] = doi

                                if article_title_tr:
                                    final_article_data["articleTitle"]["TR"] = article_title_tr
                                if article_title_eng:
                                    final_article_data["articleTitle"]["ENG"] = article_title_eng

                                if abstract_tr or abstract_eng:
                                    if abstract_eng:
                                        final_article_data["articleAbstracts"]["ENG"] = abstract_eng
                                    if abstract_tr:
                                        final_article_data["articleAbstracts"]["TR"] = abstract_tr

                                if azure_article_data:
                                    if azure_article_data.get("article_keywords", None):
                                        if azure_article_data["article_keywords"].get("tr", None):
                                            final_article_data["articleKeywords"]["TR"] = \
                                                azure_article_data["article_keywords"]["tr"]
                                        if azure_article_data["article_keywords"].get("eng", None):
                                            final_article_data["articleKeywords"]["ENG"] = \
                                                azure_article_data["article_keywords"]["eng"]

                                        if azure_article_data.get("article_authors", None):
                                            final_article_data["articleAuthors"] = azure_article_data["article_authors"]
                                        elif authors:
                                            final_article_data["articleAuthors"] = Author.author_to_dict(authors)

                                elif keywords_tr or keywords_eng:
                                    if keywords_tr:
                                        final_article_data["articleKeywords"]["TR"] = keywords_tr
                                    if keywords_eng:
                                        final_article_data["articleKeywords"]["ENG"] = keywords_eng

                                if dergipark_references:
                                    final_article_data["articleReferences"] = dergipark_references
                                elif with_adobe and adobe_references:
                                    final_article_data["articleReferences"] = adobe_references
                        if with_azure:
                            with open(os.path.join(r'C:\Users\emine\OneDrive\Masaüstü\outputs\\',
                                                   "azure_" + common.helpers.methods.others.generate_random_string(7)),
                                      "w",
                                      encoding='utf-8') as f:
                                f.write(json.dumps(azure_article_data, indent=4, ensure_ascii=False))
                        with open(os.path.join(r'C:\Users\emine\OneDrive\Masaüstü\outputs\\',
                                               common.helpers.methods.others.generate_random_string(7)), "w",
                                  encoding='utf-8') as f:
                            f.write(json.dumps(final_article_data, indent=4, ensure_ascii=False))

                        print(json.dumps(azure_article_data, indent=4, ensure_ascii=False))
                        clear_directory(download_path)
                        create_logs(True, get_logs_path(parent_type, file_reference))
                        i += 1
        else:
            log_already_scanned(get_logs_path(parent_type, file_reference))
        if random.random() < 0.2:  # In the long run sends 20% of the outputs as WP message
            send_example_log(final_article_data)
        return timeit.default_timer() - start_time
    except Exception as e:
        send_notification(
            GeneralError(f"An error encountered and cought by outer catch while scraping Dergipark journal"
                         f"{journal_name} with article number {i}. Error encountered was: {e}."))
        clear_directory(download_path)
        return timeit.default_timer() - start_time


if __name__ == "__main__":
    print(get_logs_path("bol", "mol"))
    create_logs(True, "foo", "bar")
