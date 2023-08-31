import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# Open the webpage
driver.get('https://onkder.org/archive.php')

try:
    time.sleep(1)
    # Wait for the element to be clickable
    element = driver.find_element(By.CSS_SELECTOR, 'a[data-toggle="collapse"][href="#id_2023"]')

    # Click the element to toggle the collapse
    element.click()

    time.sleep(1)
    element = driver.find_element(By.ID, 'id_2023')

    contents = element.find_elements(By.TAG_NAME, 'a')
    print(contents[0].get_attribute('href'))

except Exception as e:
    print(e)

finally:
    # Quit the browser
    driver.quit()
