import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

# Initiate the browser
options = Options()
# options.page_load_strategy = 'eager'
options.add_argument("--disable-notifications")
options.add_argument('--ignore-certificate-errors')
service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

driver.get('https://northclinist.com/jvi.aspx?pdir=nci&plng=eng&list=pub')
    
try:

    time.sleep(1)
    element = driver.find_element(By.CSS_SELECTOR, '.col-xs-12.col-sm-6.col-md-6.col-lg-6')

    contents = element.find_elements(By.TAG_NAME, 'a')
    print(contents[len(contents)-1].get_attribute('href'))

except Exception as e:
    print(e)

finally:
    # Quit the browser
    driver.quit()
