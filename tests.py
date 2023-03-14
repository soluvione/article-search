# Python libraries
import time
import os
# Local imports

# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from services.send_sms import send_sms
from common.erorrs import ParseError
from selenium.common.exceptions import WebDriverException
# Webdriver options
options = Options()
options.add_experimental_option('prefs',  {"plugins.always_open_pdf_externally": True})
options.page_load_strategy = 'eager'
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://www.google.com")
send_sms(ParseError("merhabaa"))
