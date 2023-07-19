def get_imports():
    return '''import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

'''


def get_web_driver():
    return '''# Initiate the browser
options = Options()
# options.page_load_strategy = 'eager'
options.add_argument("--disable-notifications")
options.add_argument('--ignore-certificate-errors')
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

'''


def get_base_url(base_url):
    return f'driver.get(\'{base_url}\')'


def click_element(element):
    return f'''
    time.sleep(1)
    element = driver.find_element(By.CSS_SELECTOR, '{element}')
    element.click()

    '''


def find_elements(enum, element):
    return f'''
    time.sleep(1)
    element = driver.find_element({get_enum(enum)}, '{element}')

    '''


def get_enum(by):
    if by == 'id':
        return 'By.ID'
    elif by == 'tag':
        return 'By.TAG_NAME'
    elif by == 'class':
        return 'By.CLASS_NAME'
    else:
        return 'By.CSS_SELECTOR'


def start_try_catch():
    return '''
    
try:
'''


def end_try_catch():
    return '''except Exception as e:
    print(e)

finally:
    # Quit the browser
    driver.quit()
'''
