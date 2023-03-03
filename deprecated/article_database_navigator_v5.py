"""
This script has finished its job. Scraped all the articles and their links.
"""

# Python libraries
import time
import csv

# Local imports

# 3rd Party libraries
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
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
journal_name_list = []
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
time.sleep(2)
page_source = driver.page_source
page_soup = BeautifulSoup(page_source, 'html.parser')
k = 0
for element in page_soup.find_all(class_='journal'):
    journal_name_list.append(element.text[element.text.index('.')+1:])


with open('dict6.csv', 'w', encoding='utf_8_sig') as output:
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    writer.writerow(journal_name_list)
#
# original_window = driver.current_window_handle
# original_address = driver.current_url
# is_found= True
# driver.execute_script("window.scrollBy(0, 12896)")
# time.sleep(5)
# for i in range(497, 595):
#
#     # try:
#     #     WebDriverWait(driver, 5).until(EC.visibility_of_element_located(
#     #         (By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a'))).click()
#     # except Exception:
#     #     is_found = False
#     #     k = 1
#     #     ActionChains(driver).scroll_by_amount(0, -50000).perform()
#     #     while True:
#     #         if not is_found:
#     #             try:
#     #                 ActionChains(driver) \
#     #                     .scroll_by_amount(0, 100 * k) \
#     #                     .perform()
#     #                 WebDriverWait(driver, 1).until(EC.visibility_of_element_located(
#     #                     (By.XPATH,
#     #                      f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a')))
#     #                 is_found = True
#     #             except:
#     #                 k += 1
#     #         break
#     try:
#         time.sleep(0.75)
#         # ActionChains(driver) \
#         #     .scroll_by_amount(0, (i*1)) \
#         #     .perform()
#         # time.sleep(1)
#         driver.execute_script("window.scrollBy(0, 26)")
#         time.sleep(0.5)
#         #ActionChains(driver).move_to_element(driver.find_element(By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i+10}]/a'))
#         WebDriverWait(driver, 15).until(EC.presence_of_element_located(
#             (By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a'))).click()
#         time.sleep(1)
#         # driver.find_element(By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i+1}]/a').click()
#         article_page = driver.current_window_handle
#         try:
#
#             try:
#                 # journal_name = driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/section[1]/div/div/div[1]/div/div/div[2]/div/table/tr[1]/td[2]').text
#                 # journal_name_list.append(journal_name)
#                 driver.set_page_load_timeout(10)
#                 page_button = WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.XPATH,
#                                                                                                '//*[@id="__layout'
#                                                                                                '"]/div/div['
#                                                                                                '1]/section['
#                                                                                                '1]/div/div/div['
#                                                                                                '2]/div/div/div['
#                                                                                                '1]/button')))
#                 driver.execute_script("arguments[0].click();", page_button)
#                 # ActionChains(driver).move_by_offset(download_button_location['x'], download_button_location[
#                 # 'y']).click().perform() driver.find_element(By.XPATH, '//*[@id="__layout"]/div/div[1]/section[
#                 # 1]/div/div/div[2]/div/div/div[1]/button').click()
#                 WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
#                 for window_handle in driver.window_handles:
#                     if window_handle != article_page:
#                         driver.switch_to.window(window_handle)
#                         break
#
#                 url_of_page = driver.current_url
#                 print(url_of_page)
#                 url_list_final.append(url_of_page)
#                 with open('scanned_articles497dan.json', 'w', encoding='utf-8') as f:
#                     f.write(json.dumps(dict(zip(journal_name_list, url_list_final)), indent=4, ensure_ascii=False))
#                 time.sleep(2)
#                 while len(driver.window_handles) != 1:
#                     driver.switch_to.window(driver.window_handles[-1])
#                     driver.close()
#                 driver.switch_to.window(original_window)
#                 time.sleep(1.5)
#             except Exception:
#                 url_list_final.append("Null or Not Operations Web Page")
#                 driver.switch_to.window(original_window)
#                 time.sleep(1.5)
#
#         except Exception:
#             pass
#
#
#         if str(driver.current_url) != "https://www.atifdizini.com/journals?char=ALL&index=100":
#             driver.back()
#             time.sleep(1)
#         print(i+1)
#     except Exception:
#         driver.execute_script("window.scrollBy(0, 75)")
#         time.sleep(0.75)
#         # ActionChains(driver) \
#         #     .scroll_by_amount(0, (i*1)) \
#         #     .perform()
#         # time.sleep(1)
#         driver.execute_script("window.scrollBy(0, 26)")
#         time.sleep(0.5)
#         # ActionChains(driver).move_to_element(driver.find_element(By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i+10}]/a'))
#         WebDriverWait(driver, 15).until(EC.presence_of_element_located(
#             (By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i + 1}]/a'))).click()
#         time.sleep(0.5)
#         # driver.find_element(By.XPATH, f'//*[@id="__layout"]/div/section[1]/div/div/div[1]/div/div/div/div[2]/div[{i+1}]/a').click()
#
#         try:
#
#             try:
#                 # journal_name = driver.find_element(By.XPATH, '/html/body/div/div/div/div[1]/section[1]/div/div/div[1]/div/div/div[2]/div/table/tr[1]/td[2]').text
#                 # journal_name_list.append(journal_name)
#                 driver.set_page_load_timeout(10)
#                 page_button = WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.XPATH,
#                                                                                                '//*[@id="__layout'
#                                                                                                '"]/div/div['
#                                                                                                '1]/section['
#                                                                                                '1]/div/div/div['
#                                                                                                '2]/div/div/div['
#                                                                                                '1]/button')))
#                 driver.execute_script("arguments[0].click();", page_button)
#                 # ActionChains(driver).move_by_offset(download_button_location['x'], download_button_location[
#                 # 'y']).click().perform() driver.find_element(By.XPATH, '//*[@id="__layout"]/div/div[1]/section[
#                 # 1]/div/div/div[2]/div/div/div[1]/button').click()
#                 WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
#                 for window_handle in driver.window_handles:
#                     if window_handle != article_page:
#                         driver.switch_to.window(window_handle)
#                         break
#
#                 url_of_page = driver.current_url
#                 url_list_final.append(url_of_page)
#
#                 time.sleep(2)
#                 while len(driver.window_handles) != 1:
#                     driver.switch_to.window(driver.window_handles[-1])
#                     driver.close()
#                 driver.switch_to.window(original_window)
#                 time.sleep(1.5)
#             except Exception:
#                 url_list_final.append("Null or Not Operations Web Page")
#                 driver.switch_to.window(original_window)
#                 time.sleep(1.5)
#         except Exception:
#             pass
#
#         if str(driver.current_url) != "https://www.atifdizini.com/journals?char=ALL&index=100":
#             driver.back()
#         print(i + 1)
#         with open('scanned_articles497dan.json', 'w', encoding='utf-8') as f:
#             f.write(json.dumps(dict(zip(journal_name_list, url_list_final)), indent=4, ensure_ascii=False))
#
# print(url_list_final)
# print(len(url_list_final))
#
# with open('scanned_articles497dan.json', 'w', encoding='utf-8') as f:
#     f.write(json.dumps(dict(zip(journal_name_list, url_list_final)), indent=4, ensure_ascii=False))
# """"
#
#
# but = driver.find_element(By.XPATH, '/html/body/div/div/div/div/section[2]/div/div[1]/ul/li[4]')
# but = driver.find_element(By.XPATH, '/html/body/div/div/div/div/section[2]/div/div[1]/ul/
# ActionChains(driver).move_by_offset(location['x'], location['y']).click().perform()
# location = but.location
#
#
# journal_elements = driver.find_elements(By.CLASS_NAME, 'journal')
# href_list = []
# for element in journal_elements:
#     href_list.append(element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
#
# """
