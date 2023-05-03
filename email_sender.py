from datetime import datetime
import time
import os
import glob
import re
import json
from pathlib import Path
# Local imports
from classes.author import Author
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.scrape_helpers.check_download_finish import check_download_finish
from common.helpers.methods.scrape_helpers.clear_directory import clear_directory
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.helpers.methods.scrape_helpers.drgprk_helper import author_converter, identify_article_type
from common.helpers.methods.scrape_helpers.drgprk_helper import reference_formatter, format_file_name
from common.services.post_json import post_json
from common.services.send_sms import send_notification
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser
# 3rd Party libraries
import requests
from selenium import webdriver
from selenium.webdriver import ActionChains, Keys
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
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://eposta.tccb.gov.tr/")
driver.maximize_window()
time.sleep(5)
username = driver.find_element(By.XPATH, '//*[@id="username"]')
username.send_keys("ismetemin.soyvural")
password = driver.find_element(By.XPATH, '//*[@id="password"]')
password.send_keys("Tccb-16032023")
time.sleep(1)
sign_in = driver.find_element(By.XPATH, '/html/body/form/div/div[2]/div/div[9]/div')
sign_in.click(),
time.sleep(4)
new_button = driver.find_element(By.XPATH,
                                 '//*[@id="primaryContainer"]/div[5]/div/div[1]/div/div[5]/div[1]/div/div[1]/div/div/div[1]/div/button[1]')

while True:
    time.sleep(1)
    driver.find_element(By.XPATH,
                        '//*[@id="primaryContainer"]/div[5]/div/div[1]/div/div[5]/div[1]/div/div[1]/div/div/div[1]/div/button[1]').click()
    time.sleep(3)
    send_to_box = driver.find_element(By.XPATH, '/html/body/div[2]/div/div[3]/div[5]/div/div[1]/div/div[5]/div[3]/div/div[5]/div[1]/div/div[3]/div[4]/div/div[1]/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/div[1]/div/div/div/span/div[1]/form/input')
    ActionChains(driver).click(send_to_box).send_keys("eminens06@gmail.com").pause(1).send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys(Keys.TAB).send_keys("This is the title of an automated message!").pause(1).send_keys(Keys.TAB).send_keys("Hi!\n\nThis is the body of the text!\n\nHave a nice day!").perform()
    send_button = driver.find_element(By.XPATH, '//*[@id="primaryContainer"]/div[5]/div/div[1]/div/div[5]/div[3]/div/div[5]/div[1]/div/div[3]/div[4]/div/div[1]/div[2]/div[3]/div[2]/div[1]/button[1]')
    input("Continue with the next mail?")
    send_button.click()
time.sleep(300)
