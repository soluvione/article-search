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
from common.helpers.methods.common_scrape_helpers.drgprk_helper import author_converter
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
# Webdriver options
# Eager option shortens the load time. Always download the pdfs and does not display them.
options = Options()
options.page_load_strategy = 'eager'
download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
options.add_experimental_option('prefs', prefs)
options.add_argument("--disable-notifications")
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)


# Aves journals' latest issue is on the main page all the time.
# You need to scroll the aves articles down

driver.get("https://www.advancedotology.org/")

# Scroll to the bottom
start = timeit.default_timer()
while timeit.default_timer() - start < 10:
    driver.execute_script("window.scrollBy(0,500)")
    time.sleep(0.2)