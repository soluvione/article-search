# Python libraries
import json
import time

# Local imports
from helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
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
options.page_load_strategy = 'eager'
options.add_experimental_option('prefs', {"plugins.always_open_pdf_externally": True})
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

scrape_type = "A_UNQ"
pdf_scrape_type = "S_UNQ"
start_page_url = "https://www.psikolog.org.tr/tr/yayinlar/yazilar/"
driver.get(start_page_url)

# START SCRAPING
recent_issue_element = driver.find_element(By.CSS_SELECTOR, 'li.group')
recent_vol = int(recent_issue_element.text.split()[1])
is_scanned = True

# This journal sometimes publishes special editions. So if there is a special ed. then issue num is 0.
if recent_issue_element.text.split()[-1] == "Sayı":
    recent_issue = recent_issue_element.text.strip()
    with open('latest_scanned_special_issue.json', encoding='utf-8') as file:
        latest_scanned_issue = json.load(file)
        if not latest_scanned_issue == recent_issue:
            is_scanned = False

    # START DOWNLOADS IF APPROPRIATE
    if not is_scanned:
        expand_but = driver.find_element(By.XPATH, '//*[@id="pageContent"]/div/div/div[2]/div[2]/ul/li[1]/div/span')
        expand_but.click()
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, 100)")
        time.sleep(1)
        url_list = []
        issue_elements = recent_issue_element.find_elements(By.CSS_SELECTOR, 'li.item')

        # GET URL VALUES FOR EACH PDF
        for element in issue_elements:
            if "Kapak" not in element.text:
                pdf_elements = element.find_element(By.CSS_SELECTOR, 'div.columns.shrink')
                url_list.append(pdf_elements.find_elements(By.TAG_NAME, 'a')[-1].get_attribute('href'))

        # GO AND DOWNLOAD PDFS IF THE URL IS NOT SCANNED
        for url in url_list:
            if not is_article_scanned_url(url=url, path_=__file__):
                driver.get(url)
                # TODO WAIT UNTIL DOWNLOADED
                time.sleep(1)
                update_scanned_articles(url=url, is_doi=False, path_=__file__)
            else:
                print("Article is scanned!")

        with open('latest_scanned_special_issue.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(recent_issue))
else:
    recent_issue = int(recent_issue_element.text.split()[-1])
    is_scanned = is_issue_scanned(vol_num=recent_vol, issue_num=recent_issue, path_=__file__)
    if is_scanned:
        print("The article issue is already scanned!")

    # START DOWNLOADS IF APPROPRIATE
    if not is_scanned:
        expand_but = driver.find_element(By.XPATH, '//*[@id="pageContent"]/div/div/div[2]/div[2]/ul/li[1]/div/span')
        expand_but.click()
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, 100)")
        time.sleep(1)
        url_list = []
        issue_elements = recent_issue_element.find_elements(By.CSS_SELECTOR, 'li.item')

        # GET URL VALUES FOR EACH PDF
        for element in issue_elements:
            if "Kapak" not in element.text:
                pdf_elements = element.find_element(By.CSS_SELECTOR, 'div.columns.shrink')
                url_list.append(pdf_elements.find_elements(By.TAG_NAME, 'a')[-1].get_attribute('href'))

        # GO AND DOWNLOAD PDFS IF THE URL IS NOT SCANNED
        for url in url_list:
            if not is_article_scanned_url(url=url, path_=__file__):
                driver.get(url)
                # TODO WAIT UNTIL DOWNLOADED
                time.sleep(1)
                update_scanned_articles(url=url, is_doi=False, path_=__file__)
            else:
                print("Article is scanned!")
        update_scanned_issues(vol_num=recent_vol, issue_num=recent_issue, path_=__file__)

driver.close()
