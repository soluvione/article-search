"""
This is the template scraper that will be used to multiply.
this is a change
"""
# Python libraries
import time
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
    abstract_formatter
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

# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Metadata about the journal
# Scrape types has 2 options, either unique (A_UNQ) or Dergipark (A_DRG). PDF scrape types can vary more than that.
journal_name = f"Genel Sağlık Bilimleri Dergisi"
scrape_type = "A_DRG"
pdf_scrape_type = "A_UNQ"
pages_to_send = 1
start_page_url = f"https://dergipark.org.tr/tr/pub/jgehes"
adobe_references = None
"""
SPECIAL NOTES REGARDING THE JOURNAL (IF APPLICABLE)

"""

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
with_azure = True
with_adobe = False
# START DOWNLOADS IF ISSUE IS NOT SCANNED
if True:
    dergipark_components.go_to_issue_page(driver, latest_publication_element, journal_name, recent_volume, recent_issue)

    issue_year = dergipark_components.scrape_year_information(driver)

    # Get all elements
    article_elements = dergipark_components.scrape_article_elements(driver, journal_name, recent_volume, recent_issue)

    # Add URLs to article URLs list
    dergipark_components.scrape_article_urls(driver, article_elements, article_url_list, journal_name, recent_volume,
                                             recent_issue)

    # GET TO THE ARTICLE PAGE AND TRY TO DOWNLOAD AND PARSE THE ARTICLE PDFs
    article_num = 0
    for i in range(3):  # article_url in article_url_list
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

                pdf_to_download_available = dergipark_components.download_article_pdf(driver)

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
                        location_header = AzureHelper.analyse_pdf(first_pages_cropped_pdf)  # Location header is the response
                    # address of Azure API
                    if with_adobe and pdf_scrape_type != "A_DRG & R":
                        adobe_pdf = split_in_half(formatted_name)

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
                                abstract_tr = abstract_formatter(element.find_element(By.TAG_NAME, 'p').text, "tr")
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
                                abstract_eng = abstract_formatter(element.find_element(By.TAG_NAME, 'p').text, "eng")
                        for element in keywords_elements:
                            if element.text:
                                for keyword in element.find_element(By.TAG_NAME, 'p').text.split(','):
                                    if keyword.strip() and keyword.strip() not in keywords_eng:
                                        keywords_eng.append(keyword.strip())

                # MULTIPLE LANGUAGE ARTICLES
                elif article_lang_num == 2:
                    tr_article_element, article_title_tr, abstract_tr = dergipark_components.get_turkish_data(driver, language_tabs)

                    try:
                        keywords_element = dergipark_components.get_multiple_lang_article_keywords(tr_article_element)

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

                    eng_article_element, article_title_eng, abstract_eng_element = dergipark_components.get_english_data(driver)

                    for part in abstract_eng_element:
                        if part.get_attribute('innerText'):
                            abstract_eng = abstract_formatter(part.get_attribute('innerText'), "eng")
                    keywords_element = dergipark_components.get_multiple_lang_article_keywords(eng_article_element)

                    for keyword in keywords_element.find_element(By.TAG_NAME, 'p').get_attribute(
                            'innerText').strip().split(','):
                        if keyword.strip():
                            keywords_eng.append(keyword.strip())
                    keywords_eng[-1] = re.sub(r'\.', '', keywords_eng[-1])

                    button = driver.find_element(By.XPATH, '//*[@id="show-reference"]')
                    button.click()
                    time.sleep(0.4)
                    reference_list_elements = dergipark_components.get_multiple_lang_article_refs(eng_article_element)
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
                try:
                    doi = dergipark_components.get_doi(driver)
                    doi = doi[doi.index("org/") + 4:]
                except Exception as e:
                    send_notification(e)
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
                            azure_article_data = AzureHelper.format_general_azure_data(azure_data=azure_data)
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
                                        "articlePage Range": article_page_range,
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
                                    final_article_data["articleKeywords"]["TR"] = azure_article_data["article_keywords"]["tr"]
                                if azure_article_data["article_keywords"].get("eng", None):
                                    final_article_data["articleKeywords"]["ENG"] = azure_article_data["article_keywords"]["eng"]
                        elif keywords_tr or keywords_eng:
                            if keywords_tr:
                                final_article_data["articleKeywords"]["TR"] = keywords_tr
                            if keywords_eng:
                                final_article_data["articleKeywords"]["ENG"] = keywords_eng

                        if authors:
                            final_article_data["articleAuthors"] = Author.author_to_dict(authors)

                        if dergipark_references:
                            final_article_data["articleReferences"] = dergipark_references
                        elif with_adobe and adobe_references:
                            final_article_data["articleReferences"] = adobe_references
                # print(pprint.pprint(final_article_data))
                if with_azure:
                    with open(os.path.join(r'C:\Users\emine\OneDrive\Masaüstü\outputs\\', "azure_" + common.helpers.methods.others.generate_random_string(7)), "w", encoding='utf-8') as f:
                        f.write(json.dumps(azure_article_data, indent=4, ensure_ascii=False))
                with open(os.path.join(r'C:\Users\emine\OneDrive\Masaüstü\outputs\\', common.helpers.methods.others.generate_random_string(7)), "w", encoding='utf-8') as f:
                    f.write(json.dumps(final_article_data, indent=4, ensure_ascii=False))

                print(json.dumps(azure_article_data, indent=4, ensure_ascii=False))
                clear_directory(download_path)
