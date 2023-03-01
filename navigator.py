# Python libraries
import time
import re
import json
from datetime import date

# Local imports
from journal import Journal

# 3rd Party libraries
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.page_load_strategy = 'eager'
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
url_list_final = []
driver.get("https://www.atifdizini.com/login")

time.sleep(4)

username_box = driver.find_element(By.XPATH, '//*[@id="__layout"]/div/section[1]/div/div/div['
                                             '1]/div/div/div/fieldset/form/div[1]/div/div/input')
password_box = driver.find_element(By.XPATH, '//*[@id="__layout"]/div/section[1]/div/div/div['
                                             '1]/div/div/div/fieldset/form/div[2]/div/div/input')
enter_button = driver.find_element(By.XPATH, '//*[@id="__layout"]/div/section[1]/div/div/div['
                                             '1]/div/div/div/fieldset/form/div[3]/div/button')
username_box.send_keys("eminens06@gmail.com")
password_box.send_keys("h9quxA0vCx")
time.sleep(1)
enter_button.click()
time.sleep(5)
WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
    (By.XPATH, '//*[@id="__layout"]/div/div[1]/div/section[2]/div/div[2]/img'))).click()
# img = driver.find_element(By.XPATH, '//*[@id="__layout"]/div/div[1]/div/section[2]/div/div[2]/img')
time.sleep(2)
# img.click()
time.sleep(3)
WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
    (By.XPATH, '//*[@id="__layout"]/div/div[1]/div/div/div/div/section/ul/li[4]/a'))).click()
# yay = driver.find_element(By.XPATH, '//*[@id="__layout"]/div/div[1]/div/div/div/div/section/ul/li[4]/a')

# yay.click()
time.sleep(3)

# but.click()
# time.sleep(2)
all_button = driver.find_element(By.XPATH, '//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/ul[2]/li[33]')
all_button.click()

original_window = driver.current_window_handle
is_found= True
for i in range(595):

    try:
        WebDriverWait(driver, 5).until(EC.visibility_of_element_located(
            (By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a'))).click()
    except Exception:
        is_found = False
        k = 1
        ActionChains(driver).scroll_by_amount(0, -50000).perform()
        while True:
            if not is_found:
                try:
                    ActionChains(driver) \
                        .scroll_by_amount(0, 100 * k) \
                        .perform()
                    WebDriverWait(driver, 1).until(EC.visibility_of_element_located(
                        (By.XPATH,
                         f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a')))
                    is_found = True
                except:
                    k += 1
            break
    try:
        # ActionChains(driver) \
        #     .scroll_by_amount(0, 15*i) \
        #     .perform()
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located(
            (By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a'))).click()
        # driver.find_element(By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i+1}]/a').click()

        try:

            article_page = driver.current_window_handle
            try:
                page_button = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH,
                                                                                               '//*[@id="__layout'
                                                                                               '"]/div/div['
                                                                                               '1]/section['
                                                                                               '1]/div/div/div['
                                                                                               '2]/div/div/div['
                                                                                               '1]/button')))
                driver.execute_script("arguments[0].click();", page_button)
                # ActionChains(driver).move_by_offset(download_button_location['x'], download_button_location[
                # 'y']).click().perform() driver.find_element(By.XPATH, '//*[@id="__layout"]/div/div[1]/section[
                # 1]/div/div/div[2]/div/div/div[1]/button').click()
                WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                for window_handle in driver.window_handles:
                    if window_handle != article_page:
                        driver.switch_to.window(window_handle)
                        break

                url_of_page = driver.current_url
                url_list_final.append(url_of_page)
                time.sleep(2)
                driver.close()
                driver.switch_to.window(article_page)
            except Exception:
                url_list_final.append("Null")
        except Exception:
            print("elementi buldu ama erticle pageye giremedi")

        driver.back()
        print(i+1)
    except Exception:
        print("elementi asıl listede bulamadı")

print(url_list_final)
print(len(url_list_final))

with open('scanned_articles.json', 'w') as f:
    f.write(json.dumps(url_list_final, indent=4))
""""


but = driver.find_element(By.XPATH, '/html/body/div/div/div/div/section[2]/div/div[1]/ul/li[4]')
but = driver.find_element(By.XPATH, '/html/body/div/div/div/div/section[2]/div/div[1]/ul/
ActionChains(driver).move_by_offset(location['x'], location['y']).click().perform()
location = but.location


journal_elements = driver.find_elements(By.CLASS_NAME, 'journal')
href_list = []
for element in journal_elements:
    href_list.append(element.find_element(By.TAG_NAME, 'a').get_attribute('href'))

"""
