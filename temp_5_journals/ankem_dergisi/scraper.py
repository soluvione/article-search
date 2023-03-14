# Python libraries
import time

# Local imports
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned

# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
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
pdf_scrape_type = ""
start_page_url = "https://www.ankemdernegi.org.tr/index.php/yayinlanmis-sayilar"
driver.get(start_page_url)

# START SCRAPING
recent_journals_box_element = driver.find_element(By.XPATH, '/html/body/section[3]/div/div[1]/div['
                                                            '2]/div/article/section/table/tbody/tr[1]')

temp_recent_volume_text = driver.find_element(By.XPATH, '/html/body/section[3]/div/div[1]/div['
                                                   '2]/div/article/section/table/tbody/tr[1]/td[1]/p[2]/span/b').text
temp = ""
for char in temp_recent_volume_text:
    if char.isnumeric():
        temp += char

recent_volume = int(temp)
# This issue element can be a string if they publish a congress text which they haven't since 2015
recent_issue = int(recent_journals_box_element.text.split()[-1])

# START DOWNLOADS IF RECENT VOL-ISSUE NOT SCANNED BEFORE
if not is_issue_scanned(vol_num=recent_volume, issue_num=recent_issue, path_=__file__):
    # if not is_issue_scanned(recent_volume, recent_issue, __file__):
    issue_link = driver.find_element(By.XPATH, f'/html/body/section[3]/div/div[1]/div[2]/div/article/section'
                                               f'/table/tbody/tr[1]/td[{recent_issue + 1}]/a').get_attribute('href')

    driver.get("https://www.ankemdernegi.org.tr/index.php/ankem-dergisi-yil-2021-cilt-35-sayi-1")
    articles = driver.find_elements(By.TAG_NAME, 'tr')
    elems_with_articles = []
    for elem in articles:
        if "[s." in elem.text:
            driver.get(elem.find_element(By.TAG_NAME, 'a').get_attribute('href'))
            time.sleep(1)

    update_scanned_issues(recent_volume, recent_issue, __file__)

driver.close()