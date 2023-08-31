# import time
# import re
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service as ChromeService
# from webdriver_manager.chrome import ChromeDriverManager
#
# from scrapers.pkp_scraper import check_url
#
# options = Options()
# options.page_load_strategy = 'eager'
# download_path = "get_downloads_path(parent_type, file_reference)"
# prefs = {"plugins.always_open_pdf_externally": True, "download.default_directory": download_path}
# options.add_experimental_option('prefs', prefs)
# options.add_argument("--disable-notifications")
# options.add_argument('--ignore-certificate-errors')
# # options.add_argument("--headless")  # This line enables headless mode
# service = ChromeService(executable_path=r"/home/ubuntu/driver/chromedriver")
#
# # Your URLs string
# #urls_string iku bu olacak http://journals.iku.edu.tr/sybd/index.php/sybd
# urls_string = ('https://jarengteah.org/jvi.aspx?pdir=respircase&plng=tur&list=pub, https://shydergisi.org/jvi.aspx?pdir=shyd&plng=tur&list=pub,'
# 'https://medicaljournal-ias.org/jvi.aspx?pdir=ias&plng=eng&list=pub, https://tjn.org.tr/jvi.aspx?pdir=tjn&plng=eng&list=pub')
#
# # Use a regex to extract the URLs from the string
# urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', urls_string)
#
# urls = [check_url(url) for url in urls]
# # Initialize the Chrome driver
# with webdriver.Chrome(service=service, options=options) as driver:
#
#     # Open the first URL
#     driver.get(check_url(urls[0]))
#
#     # For remaining URLs, open each in a new tab
#     for url in urls[1:]:
#         # Open a new tab
#         driver.execute_script("window.open('');")
#
#         # Switch to the new tab
#         driver.switch_to.window(driver.window_handles[-1])
#
#         # Open URL in new tab
#         driver.get(url)
#
#     # After opening all tabs, switch to the first tab
#     driver.switch_to.window(driver.window_handles[0])
#     time.sleep(6000)
import pandas as pd
import re
from urllib.parse import urlparse

# Your URLs string
urls_string = "http://jeurmeds.org"

# Use a regex to extract the URLs from the string
urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', urls_string)

# Remove duplicates and convert to DataFrame
urls_df = pd.DataFrame(list(set(urls)), columns=['URLs'])

# Extract root domain from each URL
urls_df['URLs'] = urls_df['URLs'].apply(lambda url: urlparse(url).netloc)

# Write to Excel
urls_df.to_excel('urls.xlsx', index=False)

# Assuming that the original Excel file is 'original.xlsx' and
# the first column contains the journal names and the second column contains the URLs.
original_df = pd.read_excel(r'..\..\..\ProjectFiles\all_journals_n_links.xlsx', header=None, names=['Names', 'URLs'])

# Extract root domain from each URL
original_df['URLs'] = original_df['URLs'].apply(lambda url: urlparse(url).netloc)

# Merge the original DataFrame with the new DataFrame based on URLs
merged_df = pd.merge(original_df, urls_df, how='inner', on='URLs')

# Write the merged DataFrame to a new Excel file
merged_df.to_excel('crossed.xlsx', index=False)
