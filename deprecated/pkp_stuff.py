import pprint
# Python libraries
from datetime import datetime
import time
import os
import glob
import re
import json
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

import common.helpers.methods.others
# Local imports
from classes.author import Author
from common.errors import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.common_scrape_helpers.other_helpers import check_article_type_pass
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter
from common.helpers.methods.pdf_cropper import crop_pages, split_in_half
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
from common.services.post_json import post_json
from common.services.send_notification import send_notification
from common.services.azure.azure_helper import AzureHelper
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
# Scraper body chunks
from common.helpers.methods.scraper_body_components import dergipark_components

# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
# options.page_load_strategy = 'eager'
options.add_argument('--ignore-certificate-errors')
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
#options.add_argument("--headless")  # This line enables headless mode
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")

urls = [
    'https://norosirurji.dergisi.org/archive.php',
    # 'https://agridergisi.com/', # cell padding4 sanırım ya
    'https://cts.tgcd.org.tr/archive.php',
    'http://www.cshd.org.tr/archive.php',
    'http://www.jcritintensivecare.org/archive.php',
    'https://jrespharm.com/archive.php',
    'https://vetdergikafkas.org/archive.php',
    # 'https://medicaljournal-ias.org/jvi.aspx?pdir=ias&plng=eng&list=pub', # cell padding4 sanırım ya
    'https://www.turkishjournalpediatrics.org/archive.php',
    'http://geriatri.dergisi.org/archive.php',
    'http://onkder.org/archive.php',
    'https://www.ftrdergisi.com/archive.php',
    'http://turkishneurosurgery.org.tr/archive.php'
]

with webdriver.Chrome(service=service, options=options) as driver:
    i = 0
    for url in urls:
        # ARCHIEVE PAGE TO THE LATEST ISSUE
        driver.get(url)
        driver.maximize_window()
        time.sleep(1)
        # The archive page has either two styles, list or boxes
        try:
            col_lg_element = driver.find_element(By.CSS_SELECTOR, ".col-lg-6.col-md-6.col-sm-6.col-xs-12")
        except Exception:
            col_lg_element = None

        if col_lg_element:
            year = int(col_lg_element.find_element(By.CLASS_NAME, "panel-heading").text)
            vol_issue_text = col_lg_element.find_element(By.CLASS_NAME, "list-group-item-archive").text
            numbers = re.findall(r'\d+', vol_issue_text)
            numbers = [int(i) for i in numbers]
            vol, issue = numbers
            issue_link = col_lg_element.find_element(By.CLASS_NAME, "list-group-item-archive").find_element(By.TAG_NAME, "a")\
                .get_attribute("href")
            print(vol, issue, issue_link)
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
            first_six_a_tags_with_text.pop(0) if first_six_a_tags_with_text[0].text == "2023" or first_six_a_tags_with_text[0].text == "2022" else -1

            # Identify issue number and issue link
            issue, issue_link = None, None
            for i in range(len(first_six_a_tags_with_text)):
                current_issue = re.findall(r'\d+', first_six_a_tags_with_text[i].text)
                next_issue = re.findall(r'\d+', first_six_a_tags_with_text[i + 1].text) if i + 1 < len(
                    first_six_a_tags_with_text) else None
                if int(current_issue[0]) == 2022 or int(next_issue[0]) == 2022:
                    break
                if current_issue and next_issue and int(current_issue[0]) > int(next_issue[0]):
                    issue = int(current_issue[0])
                    issue_link = urljoin(url, first_six_a_tags_with_text[i]['href'])
                    break

                elif current_issue and i + 1 == len(first_six_a_tags_with_text):
                    issue = int(current_issue[0])
                    issue_link = urljoin(url, first_six_a_tags_with_text[i]['href'])
                    break

            # Extract year
            year = int(driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME,
                                                                                 "col-md-12").text.split()[1])
            vol = None
            print(year, issue, issue_link)
            driver.get(issue_link)
            time.sleep(2)

    # urls = ["https://cts.tgcd.org.tr/content.php?id=59",
    #         "https://norosirurji.dergisi.org/content.php?id=117",
    #         "http://www.cshd.org.tr/content.php?id=75",
    #         "https://jrespharm.com/content.php?id=87",
    #         "https://vetdergikafkas.org/content.php?id=213",
    #         "https://www.turkishjournalpediatrics.org/content.php?id=125",
    #         "http://onkder.org/content.php?id=139",
    #         "https://www.ftrdergisi.com/content.php?id=326",
    #         "http://turkishneurosurgery.org.tr/content.php?id=137"]
    # for url in urls:
    #     driver.get(url)
            # ISSUE PAGE TO THE ARTICLE PAGE
            text = driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME, "col-md-12").text
            print("url is: ", url)
            try:
                text = text[text.index("Vol"):]
            except:
                text = text[text.index("Cilt"):]
            vol = int(re.findall(r'\d+', text)[0])
            soup = BeautifulSoup(
                driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME, "col-md-12").get_attribute(
                    "outerHTML"), 'html.parser')
            titles = soup.find_all('a', {'class': 'article_title'})

            # print all article titles
            for title in titles:
                print(title.get_text())
            abstract_links = soup.find_all('a', href=True, class_="btn btn-xs btn-success")

            # print all abstract links
            for link in abstract_links:
                if "abstract.php" in link['href']:
                    print(link['href'])
            if soup.find_all('span', {'style': 'color:#5c5c5c'}):
                for item in soup.find_all('span', {'style': 'color:#5c5c5c'}):
                    print(item.get_text())
            else:
                for item in soup.find_all('a', attrs={'name': True}):
                    parent_element = item.parent
                    parent_text = parent_element.text.strip()
                    print(parent_text)
            elements = soup.select('a[href]:has(span.glyphicon.glyphicon-circle-arrow-right)')
            types = []
            for element in elements:
                element_text = re.sub(r"[^A-Za-z\s]", "", element.get_text(strip=True))
                number_of_times = re.findall(r"\d+", element.get_text(strip=True))[0]
                for i in range(int(number_of_times)):
                    types.append(element_text.strip())
            print(types)

    soup = BeautifulSoup(
        driver.find_element(By.ID, "content_icerik").find_element(By.CLASS_NAME, "col-md-12").get_attribute(
            "outerHTML"), 'html.parser')
    print(soup.prettify())



    driver.get("https://onkder.org/abstract.php?id=1385")
    main_element = driver.find_element(By.ID, "icerik-alani")
    soup = BeautifulSoup(main_element.get_attribute("outerHTML"), 'html.parser')
    try:
        el = soup.find('h2').get_text(strip=True)
    except:
        el = driver.find_element(By.XPATH, '//*[@id="icerik-alani"]/div[2]/div[2]/div[1]').text
    print(el)
    try:
        authors_element = driver.find_element(By.ID, "authors_div").text.split(',')
    except:
        pass
    print(authors_element)

    def has_sup_with_text(element):
        return element.name == 'span' and element.find('sup') is not None

    span_element = soup.find_all(has_sup_with_text)[0]
    specialities = []
    n, index = 0, 0
    for char in span_element.get_text().strip():
        if char.isnumeric() and index > 0:
            specialities.append(span_element.get_text()[n + 1:index+1].strip()[1:])
            n = index
        if index == len(span_element.get_text().strip()) - 1:
            specialities.append(span_element.get_text()[n + 1:].strip()[1:])
        index += 1
    print(specialities)


    print(soup.get_text()[soup.get_text().index("DOI"):].split()[2])
    response = requests.get("https://cts.tgcd.org.tr/abstract.php?id=188")
    soup = BeautifulSoup(response.content, 'html.parser')
    meta_tag = soup.find('meta', attrs={'name': 'citation_keywords'})

    # Check if the tag is found and print the content
    if meta_tag:
        keywords = meta_tag['content']
        print(keywords)
    else:
        print("Meta tag not found!")
    soup = BeautifulSoup(main_element.get_attribute("outerHTML"), 'html.parser')

    abstract = soup.get_text()[soup.get_text().index("DOI")+20: soup.get_text().index("Keywords")].replace("\n", " ")

    print(abstract)

    download_link = start_page.replace("abtract", "pdf")