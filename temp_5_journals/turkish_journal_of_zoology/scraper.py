# Python libraries
import time

# Local imports

# 3rd Party libraries
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
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver-linux64/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

scrape_type = "A_UNQ"
pdf_scrape_type = "S_UNQ"
start_page_url = "https://journals.tubitak.gov.tr/zoology/all_issues.html"
driver.get(start_page_url)

# START SCRAPING
recent_vol = driver.find_element(By.CSS_SELECTOR, 'h2.vol').text.split()[1]
recent_issue = driver.find_element(By.CSS_SELECTOR, 'h3.issue').text.split()[-1]

# START DOWNLOADS IF APPROPRIATE
if True:  # If issue and vol is not scanned
    recent_issue_link = driver.find_element(By.CSS_SELECTOR, 'h3.issue').find_element(By.TAG_NAME, 'a').get_attribute(
        'href')
    driver.get(recent_issue_link)
    article_list_element = driver.find_element(By.CSS_SELECTOR, 'div.article-list')
    article_urls = []
    # The first article is Cover and Contents and therefore need to exclude it.
    for element in article_list_element.find_elements(By.CSS_SELECTOR, 'div.doc'):
        if not ("Cover and Contents" in element.text):
            article_urls.append(element.find_elements(By.TAG_NAME, 'a')[1].get_attribute('href'))
    print(article_urls)

    for i in range(0, len(article_urls)):
        driver.get(article_urls[i])
        if i == len(article_urls) - 1:
            download_button = WebDriverWait(driver, timeout=5).until(EC.presence_of_element_located((By.ID, 'pdf')))
            download_button.click()
            time.sleep(3)
        else:
            download_button = WebDriverWait(driver, timeout=5).until(EC.presence_of_element_located((By.ID, 'pdf')))
            download_button.click()

driver.close()
