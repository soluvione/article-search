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
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

scrape_type = "A_DRG"
pdf_scrape_type = "S_UNQ"
start_page_url = "https://dergipark.org.tr/tr/pub/hujpharm"
driver.get(start_page_url)

# START SCRAPING
latest_publication_element = driver.find_element(By.CSS_SELECTOR, '.kt-widget-18__item')
temp_txt = latest_publication_element.text  # latest_publication_text
recent_volume = int(temp_txt[temp_txt.index(":") + 1:temp_txt.index("Sayı")].strip())
recent_issue = int(temp_txt.split()[-1])

# START DOWNLOADS IF APPROPRIATE
if True: # If issue and vol is not scanned
    driver.get(latest_publication_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
    time.sleep(3)
    article_elements = driver.find_elements(By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')
    article_url_list = []
    for article in article_elements:
        article_url = article.find_element(By.CSS_SELECTOR, '.card-title.article-title').get_attribute('href')
        article_url_list.append(article_url)

    for article_url in article_url_list:
        if True:  # If article is not scanned and is confirmed by the JSON
            driver.get(article_url)
            driver.get(driver.find_element(By.CSS_SELECTOR, 'a.btn.btn-sm.float-left.article-tool.pdf.d-flex.align-items-center')
                       .get_attribute('href'))

            driver.execute_script("window.history.go(-1)")
            WebDriverWait(driver, timeout=1).until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')))



driver.close()