"""
This is the template scraper that will be used to multiply.
"""
# Python libraries
from datetime import datetime
import time
import os
import glob
import re
import json
from pathlib import Path
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.support.ui import Select
# Local imports
from classes.author import Author
from common.errors import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.common_scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter
from common.services.post_json import post_json
from common.services.send_notification import send_notification
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
# 3rd Party libraries
import pyperclip
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
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver-linux64/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

# ATIF DIZINI DATA
atif_dizini_url = "http://178.62.217.122/login"
user_name = "emin@atifdizini.com"
password = "o6q4yZ=BYOVC"

# CSS SELECTORS DATA
article_element_selectors = {"pdf_upload_button": "By.ID, 'labeluploadFile'",
                             "save_button": "By.XPATH, '/html/body/div/div[14]/main/div/div/div/div[2]/div[1]/button'",
                             "category": "By.CSS_SELECTOR, 'input[aria-label=\"Kategori\"]'",
                             "title_tr": "By.CSS_SELECTOR, 'input[aria-label=\"Başlık(Türkçe)\"]'",
                             "title_eng": "By.CSS_SELECTOR, 'input[aria-label=\"Başlık(İngilizce)\"]'",
                             "year_dropdown": "By.CSS_SELECTOR, 'input[aria-label=\"Yıl\"]'",
                             "month_dropdown": "By.CSS_SELECTOR, 'input[aria-label=\"Ay\"]'",
                             "abstract_tr": "By.CSS_SELECTOR, 'div.ql-editor.ql-blank'",
                             "keywords_tr": "By.CSS_SELECTOR, 'input[aria-label=\"Anahtar Kelimeler\"]'",
                             "abstract_eng": "By.CSS_SELECTOR, 'div.ql-editor.ql-blank'",
                             "keywords_eng": "By.CSS_SELECTOR, 'input[aria-label=\"Anahtar kelimeler (İngilizce)\"]'",
                             "footnote": "By.CSS_SELECTOR, 'input[aria-label=\"Alt Bilgi\"]'",
                             "journal_name": "By.CSS_SELECTOR, 'input[aria-label=\"Dergi Adı\"]'",
                             "vol_num": "By.CSS_SELECTOR, 'input[aria-label=\"Cilt\"]'",
                             "issue_num": "By.CSS_SELECTOR, 'input[aria-label=\"Sayı\"]'",
                             "supplement_num": "By.CSS_SELECTOR, 'input[aria-label=\"Ek\"]'",
                             "article_page_start": "By.CSS_SELECTOR, 'input[aria-label=\"Başlangıç Sayfası\"]'",
                             "references": "By.CSS_SELECTOR, 'textarea[aria-label=\"Citations\"]'",
                             "doi": "By.CSS_SELECTOR, 'input[aria-label=\"DOI\"]'",
                             "article_page_end": "By.CSS_SELECTOR, 'input[aria-label=\"Bitiş Sayfası\"]'",
                             "add_author_button": "By.XPATH, '/html/body/div/div[20]/main/div/div/div/div[2]/form/div[19]/button'",
                             "author_name": "By.CSS_SELECTOR, 'input[aria-label=\"İsim\"]'",
                             "author_box": "By.CSS_SELECTOR, 'div.ql-editor.ql-blank'",
                             }


def get_to_artc_page():
    driver.get(atif_dizini_url)
    driver.maximize_window()
    time.sleep(1)
    username_element = driver.find_elements(By.TAG_NAME, 'input')[0]
    password_element = driver.find_elements(By.TAG_NAME, 'input')[1]

    username_element.send_keys(user_name)
    password_element.send_keys(password)
    button_element = driver.find_element(By.XPATH, '/html/body/div/div[2]/main/div/div/div/div[2]/form/button')
    button_element.click()
    time.sleep(0.5)
    time.sleep(4)
    driver.get("http://178.62.217.122/add")
    time.sleep(2)


def paste_data(data, pdf_path):
    with open(r"C:\Users\emine\OneDrive\Masaüstü\data.txt", 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
    # ABSTRACT TR
    pyperclip.copy(data["Article Abstracts"]["TR"])
    abstract_tr_element = driver.find_elements(By.CSS_SELECTOR,
                                               'div.quillWrapper')[0].find_element(By.CSS_SELECTOR,
                                                                                   '.ql-editor.ql-blank')
    ActionChains(driver).click(abstract_tr_element).key_down(Keys.CONTROL).send_keys("v").key_up(
        Keys.CONTROL).perform()
    time.sleep(0.5)
    # REFERENCES
    references_data = data["Article References"]
    formatted_references_string = ""
    for reference_data in references_data:
        formatted_references_string += reference_data + "\n"
    pyperclip.copy(formatted_references_string)
    citations_element = driver.find_element(By.XPATH, '//*[@id="app"]/div[2]/form/div[17]/div/div/div[1]')
    ActionChains(driver).click(citations_element)\
        .send_keys(Keys.CLEAR).pause(1).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()


    time.sleep(0.5)
    # ABSTRACT ENG
    pyperclip.copy(data["Article Abstracts"]["ENG"])
    abstract_eng_element = driver.find_elements(By.CSS_SELECTOR,
                                               'div.quillWrapper')[1].find_element(By.CSS_SELECTOR, '.ql-editor.ql-blank')
    ActionChains(driver).click(abstract_eng_element).key_down(Keys.CONTROL).send_keys("v").key_up(
        Keys.CONTROL).perform()

    # UPLOAD
    button = driver.find_element(By.XPATH, '//*[@id="uploadFile"]')
    driver.execute_script("arguments[0].style.display = 'block';", button)
    button.send_keys(r"C:\Users\emine\Downloads\makale_metni.pdf")

    # ARTICLE CATEGORY
    category_menu = driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Kategori\"]')
    ActionChains(driver).send_keys_to_element(category_menu, data["Article Type"]).send_keys(Keys.ENTER).perform()

    # ARTICLE TITLES
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Başlık(Türkçe)\"]').send_keys(data["Article Title"]["TR"])
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Başlık(İngilizce)\"]').send_keys(data["Article Title"]["ENG"])

    # YEAR
    year_element = driver.find_element(
        By.XPATH, '/html/body/div/div[8]/main/div/div/div/div[2]/form/div[6]/div[1]/div/div[1]/div[1]/div[1]')
    article_year = int(data["Article Year"])
    if article_year == 2024:
        ActionChains(driver).click(year_element).pause(0.2).send_keys(Keys.ARROW_DOWN).pause(
            0.1).send_keys(Keys.ENTER).perform()
        time.sleep(0.25)
    elif article_year == 2023:
        ActionChains(driver).click(year_element).pause(0.2).send_keys(Keys.ARROW_DOWN).send_keys(Keys.ARROW_DOWN).pause(
            0.1).send_keys(Keys.ENTER).perform()
        time.sleep(0.25)
    else:
        ActionChains(driver).click(year_element).pause(0.2).send_keys(Keys.ARROW_DOWN).send_keys(Keys.ARROW_DOWN)\
            .send_keys(Keys.ARROW_DOWN).pause(0.1).send_keys(Keys.ENTER).perform()
        time.sleep(0.25)

    # KEYWORDS
    key_tr = driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Anahtar Kelimeler\"]')
    article_key_tr = ";".join(data["Article Keywords"]["TR"])
    if article_key_tr:
        ActionChains(driver).click(key_tr).send_keys(article_key_tr).send_keys(Keys.ENTER).perform()

    key_eng = driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Anahtar kelimeler (İngilizce)\"]')
    article_key_eng = ";".join(data["Article Keywords"]["ENG"])
    if article_key_eng:
        ActionChains(driver).click(key_eng).send_keys(article_key_eng).send_keys(Keys.ENTER).perform()

    # FOOTNOTE
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Alt Bilgi\"]').send_keys(data["Article Code"])

    # JOURNAL NAME
    journal_name = driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Dergi Adı\"]')
    ActionChains(driver).click(journal_name).send_keys(data["Journal Name"]).send_keys(Keys.ENTER).perform()

    # VOL - ISSUE - SUPPLEMENT
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Cilt\"]').send_keys(int(data["Article Volume"]))
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Sayı\"]').send_keys(int(data["Article Issue"]))
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Ek\"]').send_keys(0)

    # PAGE RANGE
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Başlangıç Sayfası\"]')\
        .send_keys(int(data["Article Page Range"][0]))
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"Bitiş Sayfası\"]')\
        .send_keys(int(data["Article Page Range"][1]))

    # DOI
    driver.find_element(By.CSS_SELECTOR, 'input[aria-label=\"DOI\"]').send_keys(data["Article DOI"])

    # AUTHORS
    auth_num = len(data["Article Authors"])
    for i in range(auth_num):
        driver.find_element(By.XPATH, '//*[@id="app"]/div[2]/form/div[19]/button').click()
        i += 1

    for i in range(1, auth_num + 1):
        # Name
        author_name_box = driver.find_elements(By.CSS_SELECTOR, 'input[aria-label=\"İsim\"]')[-i]
        if data["Article Authors"][i-1]["Is Correspondance?"]:
            ActionChains(driver).click(author_name_box)\
                .key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE)\
                .send_keys(data["Article Authors"][i - 1]["Name"] + " -- YAZAR YAZIŞMA YAZARIDIR").perform()
        else:
            ActionChains(driver).click(author_name_box)\
                .key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE)\
                .send_keys(Keys.CLEAR).send_keys(
                data["Article Authors"][i - 1]["Name"]).perform()
        # Speciality
        driver.find_elements(By.ID, 'quill-container')[-i].find_element(
            By.CSS_SELECTOR, 'div.ql-editor.ql-blank').send_keys(data["Article Authors"][i-1]["Full Speciality"])

    time.sleep(5000)


if __name__ == "__main__":
    get_to_artc_page()
    paste_data(3, 3)
