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
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter, identify_article_type
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
import timeit
import re
# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
options.add_argument("--headless")
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())


with webdriver.Chrome(service=service, options=options) as driver:
    start = "https://www.firattipdergisi.com/text.php3?id=1353"
    driver.get("http://tip.fusabil.org/")
    try:
        numbers_text = driver.find_element(By.XPATH,
                                           '/html/body/center/table[2]/tbody/tr/td[1]/table/tbody/tr[2]/td/table/tbody/tr[2]/td[2]').text
    except:
        try:
            numbers_text = driver.find_element(By.XPATH,
                                               '/html/body/center/table[2]/tbody/tr/td[2]/table/tbody/tr/td/table/tbody/tr[2]/td[2]').text
        except:
            numbers_text = driver.find_element(By.XPATH,
                                               '/html/body/center/table[2]/tbody/tr/td[1]/table/tbody/tr[2]/td/table/tbody').text
    regex = re.findall(r'\d+', numbers_text)
    year = regex[0]
    vol = regex[1]
    issue = regex[2]
    print(vol,issue,year)
    # url = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr/td[1]/table/tbody/tr[2]/td/table/tbody/tr[1]/td[3]/a')
    #
    # article_elements = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody').find_elements(By.CSS_SELECTOR, 'font[class="blue"]')
    # urls = list()
    # for el in article_elements:
    #     print(el.find_element(By.CSS_SELECTOR, 'a[class="blue"]').get_attribute('href'))
    #
    #
    # # Article Page
    # main_body_element = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody')
    # main_text = main_body_element.text
    #
    #
    # page_range = main_text[main_text.index('Sayfa(lar)')+10:main_text.index('Sayfa(lar)')+18]
    # numbers = [int(number.strip()) for number in page_range.split('-')]
    # title_tr = main_body_element.find_element(By.CSS_SELECTOR, 'font[class="head"]').text.strip()
    # author_names = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[5]').text
    # author_affiliations = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[6]').text
    # keywords = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[7]').text
    # abstract = driver.find_element(By.XPATH, '/html/body/center/table[2]/tbody/tr[9]/td[1]').text
    # references = main_text[main_text.index("Kaynaklar\n1)"): main_text.index("[ Başa")]
    # references = references[references.index("1)"): references.rfind('.')+1]
    # if "firattip" in start:
    #     abbv = "Firat Med J"
    # elif "veteriner" in start:
    #     abbv = "F.U. Vet. J. Health Sci."
    # else:
    #     abbv = "F.U. Med.J.Health.Sci."
    #
    #
    #
    # download_link = start.replace("text", "pdf")