from helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
# Python libraries
import time
import csv

# Local imports
from helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles as im
from helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_doi
from helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned

# 3rd Party libraries
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Webdriver options
options = Options()
options.add_experimental_option('prefs',  {"plugins.always_open_pdf_externally": True})
options.page_load_strategy = 'eager'
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://www.ankemdernegi.org.tr/index.php/ankem-dergisi-yil-2022-cilt-36-sayi-3")
time.sleep(1)
elem = driver.find_element(By.XPATH, '//*[@id="t3-content"]/div[2]/div/article/section/div[2]/table/tbody/tr[6]/td[1]/a')
elem.click()
time.sleep(2)
driver.switch_to.window(driver.window_handles[-1])
print(driver.current_url)

