

"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
import re
import time
import os
import glob
from pathlib import Path
# Local imports
from common.errors import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.services.post_json import post_json
from common.services.send_notification import send_notification
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_all_elements
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_text_boxes
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_font_details
from common.helpers.methods.pdf_parse_helpers.pdf_parser import get_text_with_specs
from common.helpers.methods.pdf_parse_helpers.pdf_parser import get_text_boxes
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
# 3rd Party libraries
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
download_path = os.path.dirname(os.path.abspath(__file__)) + r'\downloads'
options.add_experimental_option('prefs', {"plugins.always_open_pdf_externally": True})
options.add_experimental_option('prefs', {"download.default_directory": download_path})
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# Metadata about the journal
# Scrape types has 2 options, either unique (A_UNQ) or Dergipark (A_DRG). PDF scrape types can vary more than that.
journal_name = f"ankem_dergisi"
scrape_type = "A_UNQ"
pdf_scrape_type = "A_UNQ"
start_page_url = f"https://www.ankemdernegi.org.tr/index.php/yayinlanmis-sayilar"
font_sizes_ntypes = {"Abstract": ["ftype", "size"],
                     "Article Type": ["ftype", "size"],
                     "Authors": ["ftype", "size"],
                     "Author Info": ["ftype", "size"],
                     "Header": ["ftype", "size"],
                     "Keywords": ["ftype", "size"],
                     "References": ["ftype", "size"]}
"""
SPECIAL NOTES REGARDING THE JOURNAL (IF APPLICABLE)

"""

# GLOBAL VARS
# For a given journal issue, represents how many journal articles have been scraped successfully.
num_successfully_scraped = 0
# Either contains Article URLs or PDF links of each article element
article_url_list = []
article_download_element_list = []

# GET TO THE PAGE
if requests.head(start_page_url).status_code != 200:
    send_notification(DownServerError(f"Servers of the journal {journal_name} are down."))
    raise DownServerError(f"Servers of the journal {journal_name} are down.")
try:
    driver.get(start_page_url)
except WebDriverException:
    send_notification(ScrapePathError(f"Could not reach the webpage of {journal_name}."))
    raise ScrapePathError(f"Could not reach the webpage of {journal_name}.")

# GET THE DATA ABOUT THE LATEST ISSUE/VOLUME
try:
    recent_journals_box_element = driver.find_element(By.XPATH, '/html/body/section[3]/div/div[1]/div['
                                                                '2]/div/article/section/table/tbody/tr[1]')
except NoSuchElementException:
    send_notification(ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down."))
    raise ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down.")

temp_recent_volume_text = driver.find_element(By.XPATH, '/html/body/section[3]/div/div[1]/div['
                                                        '2]/div/article/section/table/tbody/tr[1]/td[1]/p[2]/span/b').text
temp = ""
for char in temp_recent_volume_text:
    if char.isnumeric():
        temp += char

recent_volume = int(temp)
# This issue element can be a string if they publish a congress text which they haven't since 2015
recent_issue = int(recent_journals_box_element.text.split()[-1])

# START DOWNLOADS IF ISSUE IS NOT SCANNED
if not is_issue_scanned(vol_num=recent_volume, issue_num=recent_issue, path_=__file__):
    # GET TO THE ISSUE PAGE
    try:
        driver.get(recent_journals_box_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
    except NoSuchElementException:
        send_notification(ScrapePathError(f"Could not retrieve element of the webpage of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve element of the webpage of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")
    time.sleep(1)

    try:
        issue_link = driver.find_element(By.XPATH, f'/html/body/section[3]/div/div[1]/div[2]/div/article/section'
                                                   f'/table/tbody/tr[1]/td[{recent_issue + 1}]/a').get_attribute(
            'href')
    except Exception:
        send_notification(ScrapePathError(f"Could not retrieve article urls of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve article urls of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")

    # SCRAPE ARTICLE PAGE URL OR DOWNLOAD LINK OR DOWNLOAD ITEM LOCATORS FROM EACH ELEMENT
    driver.get(issue_link)
    article_num = 0
    articles = driver.find_elements(By.TAG_NAME, 'tr')
    elems_with_articles = []
    for article in articles:
        if "[s." in article.text:
            article_url_list.append(article.find_element(By.TAG_NAME, 'a').get_attribute('href'))
            time.sleep(1)

    # TRY TO DOWNLOAD AND PARSE THE ARTICLE PDFs
    for article_url in article_url_list:
        article_num += 1
        parse_nsend_successful = True
        if not is_article_scanned_url(url=article_url, path_=__file__):
            try:
                # GET TO THE DOWNLOAD LINK OR CLICK THE DOWNLOAD BUTTON
                driver.get(article_url)
            except Exception:
                send_notification(DownloadError(
                    f"Downloading the article with num of {article_num} of the journal"
                    f" {journal_name, recent_volume, recent_issue} was "
                    f"not successful."))
                clear_directory(download_path)
                continue

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
                    continue

            path_to_pdf = max(glob.iglob(os.path.dirname(os.path.abspath(__file__)) + r'\*'), key=os.path.getmtime)
            # HARVEST DATA FROM TEXT
            article_data = {"Article Title": "",
                            "Article Type": "",
                            "Article Headline": "",
                            "Article Authors": [],
                            "Article DOI": "",
                            "Article Abstracts": {"TR": "", "ENG": ""},
                            "Article Keywords": {"TR": [], "ENG": []},
                            "Article References": []}
            try:
                uni_string = re.sub('\d', '', get_text_with_specs(path_to_pdf, 1, "ABCDEE+Calibri", 9.960000000000036)).strip()
                uni_list = []
                mixed_text_bulk = get_text_with_specs(path_to_pdf, 2, "ABCDEE+Calibri,Italic", 9.0, True,
                                                      "ABCDEE+Calibri,BoldItalic", -1, True,
                                                      "ABCDEE+Calibri,Bold", 9.960000000000036)
                article_headline = re.sub('[\n{1,4}*]', '', get_text_boxes(path_to_pdf, 1, 0))
                article_type = get_text_boxes(path_to_pdf, 1, 1)[:get_text_boxes(path_to_pdf, 1, 1).index("/")]
                article_name = re.sub('[\n{1,4}*]', '', get_text_boxes(path_to_pdf, 1, 2))
                abstract_tr = mixed_text_bulk[mixed_text_bulk.index("ÖZ") + 2:mixed_text_bulk.index("Anahtar")].strip()
                try:
                    abstract_eng = mixed_text_bulk[mixed_text_bulk.index("SUMMARY"):mixed_text_bulk.index("Keywords")][
                                   8:].strip()
                except:
                    abstract_eng = mixed_text_bulk[mixed_text_bulk.index("ABSTRACT"):mixed_text_bulk.index("Keywords")][
                                   9:].strip()
                try:
                    keywords_tr = mixed_text_bulk[mixed_text_bulk.index("Anahtar"):mixed_text_bulk.index("SUMMARY")][
                                  18:].strip().split(',')
                except Exception:
                    keywords_tr = mixed_text_bulk[mixed_text_bulk.index("Anahtar"):mixed_text_bulk.index("ABSTRACT")][
                                  18:].strip().split(',')
                keywords_eng = mixed_text_bulk[
                               mixed_text_bulk.index("Keywords:") + 9: mixed_text_bulk.index("GİRİŞ")].strip().split(
                    ',')
                for i in range(len(uni_string.split())):
                    if uni_string.split()[i].isupper():
                        if i == len(uni_string.split()) - 1:
                            uni_list.append(uni_string[last_index:])
                        else:
                            uni_list.append((uni_string[last_index:uni_string.index(uni_string.split()[i]) - 2]))
                            last_index = uni_string.index(uni_string.split()[i]) + len(uni_string.split()[i])
                string = get_text_boxes(path_to_pdf, 1, 3) + get_text_boxes(path_to_pdf, 1, 4)
                string = string[:string.index('-')] + string[string.rindex('-'):]

                temp_string = list(string)
                for i in range(len(temp_string)):
                    if temp_string[i].isnumeric() and temp_string[i - 1].isalpha():
                        if temp_string[i + 1] != ',':
                            temp_string[i + 1] = ','
                    if temp_string[i] == ',' and temp_string[i + 1] == ',':
                        temp_string[i] = " "

                string = ''.join(temp_string)
                author_list = string.split(',')
                final_author_list = []
                for element in author_list:
                    if ':' in element:
                        continue
                    no_words = True
                    for char in element:
                        if char.isalpha():
                            no_words = False
                            break
                    if no_words:
                        continue
                    new_element = author_list[author_list.index(element)].strip()
                    new_element = re.sub(r'\n', '', new_element)
                    if (new_element[-1].isnumeric() and new_element[-2].isalpha()):
                        final_author_list.append(new_element)
                        continue
                author_names = []
                author_codes = []
                for element in final_author_list:
                    author_names.append(element[:-1])
                    author_codes.append((element[-1:]))
            except Exception:
                # Does not end the iteration but only sends an SMS.
                send_notification(
                    ParseError(f"Article could not be parsed, journal: {journal_name, recent_volume, recent_issue}"
                               f", article: {article_num}."))
                clear_directory(download_path)
                continue

            # DELETE DOWNLOADED PDF
            clear_directory(download_path)

            # POST THE DATA TO THE BACKEND
            try:
                post_json(article_data)
            except Exception:
                parse_nsend_successful = False
                send_notification(DataPostError(f"Article data could not be posted to the backend, journal: "
                                                f"{journal_name, recent_volume, recent_issue}, article: {article_num}"))

            # UPDATE THE SCANNED ARTICLES LIST IF PARSED
            if parse_nsend_successful:
                update_scanned_articles(url=article_url, is_doi=False, path_=__file__)
                num_successfully_scraped += 1

if ((num_successfully_scraped / len(article_url_list)) * 100) > 80:
    update_scanned_issues(vol_num=recent_volume, issue_num=recent_issue, path_=__file__)
    send_notification(
        f"Scraping and harvesting data was successful, Journal: {journal_name, recent_volume, recent_issue}")
else:
    send_notification(GeneralError(f"Majority of the journals were not scraped {journal_name}."))

driver.close()
clear_directory(download_path)

# START SCRAPING
recent_journals_box_element = driver.find_element(By.XPATH, '/html/body/section[3]/div/div[1]/div['
                                                            '2]/div/article/section/table/tbody/tr[1]')

temp_recent_volume_text = driver.find_element(By.XPATH, '/html/body/section[3]/div/div[1]/div['
                                                        '2]/div/article/section/table/tbody/tr[1]/td[1]/p[2]/span/b').text
temp = ""
for char in temp_recent_volume_text:
    if char.isnumeric():
        temp += char

# START DOWNLOADS IF RECENT VOL-ISSUE NOT SCANNED BEFORE
if not is_issue_scanned(vol_num=recent_volume, issue_num=recent_issue, path_=__file__):
    # if not is_issue_scanned(recent_volume, recent_issue, __file__):

    update_scanned_issues(recent_volume, recent_issue, __file__)

driver.close()
