# Python libraries
import time

# Local imports
from common.helpers.methods.scan_check_append.update_scanned_issues import update_scanned_issues
from common.helpers.methods.scan_check_append.update_scanned_article import update_scanned_articles
from common.helpers.methods.scan_check_append.article_scan_checker import is_article_scanned_url
from common.helpers.methods.scan_check_append.issue_scan_checker import is_issue_scanned
from common.erorrs import ScrapePathError, DownloadError, ParseError
import common.helpers.methods.pdf_parse_helpers.pdf_parser as parser

# 3rd Party libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from services.send_sms import send_sms

# Webdriver options
options = Options()
options.page_load_strategy = 'eager'
options.add_experimental_option('prefs', {"plugins.always_open_pdf_externally": True})
service = ChromeService(executable_path=ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Metadata about the journal
journal_name = ""
scrape_type = "A_UNQ"
pdf_scrape_type = ""
start_page_url = "https://www.google.com"
font_sizes_ntypes = {"Abstract": ["ftype", "size"],
                     "Article Type": ["ftype", "size"],
                     "Authors": ["ftype", "size"],
                     "Author Info": ["ftype", "size"],
                     "Header": ["ftype", "size"],
                     "Keywords": ["ftype", "size"],
                     "References": ["ftype", "size"]}

# GLOBAL VARS
num_successfully_scraped = 0

# GET TO THE PAGE
try:
    driver.get(start_page_url)
except WebDriverException:
    send_sms(ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down."))
    raise ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down.")

# START SCRAPING
try:
    latest_publication_element = driver.find_element(By.CSS_SELECTOR, '')
except NoSuchElementException:
    send_sms(ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down."))
    raise ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down.")

temp_txt = latest_publication_element.text  # latest_publication_text
recent_volume = 0
recent_issue = 0

# START DOWNLOADS IF APPROPRIATE
if not is_issue_scanned(vol_num=recent_volume, issue_num=recent_issue, path_=__file__):
    try:
        driver.get(latest_publication_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
    except NoSuchElementException:
        send_sms(ScrapePathError(f"Could not retrieve element of the webpage of{journal_name}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve element of the webpage of{journal_name}. DOM could be changed.")
    time.sleep(1.5)

    try:
        article_elements = driver.find_elements(By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')
    except Exception:
        send_sms(ScrapePathError(f"Could not retrieve article urls of{journal_name}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve article urls of{journal_name}. DOM could be changed.")

    article_url_list = []
    article_num = 0
    for article in article_elements:
        try:
            article_url = article.find_element(By.CSS_SELECTOR, '.card-title.article-title').get_attribute('href')
            article_url_list.append(article_url)
        except Exception:
            # Does not end the iteration but only sends an SMS.
            send_sms(ScrapePathError(f"Article url does not exist for the {journal_name}, article {article_num}."))
        article_num += 1

    article_num = 0
    for article_url in article_url_list:
        parse_successfull = True
        if not is_article_scanned_url(url=article_url, path_=__file__):
            try:
                driver.get(article_url)
                driver.get(driver.find_element
                           (By.CSS_SELECTOR,
                            'a.btn.btn-sm.float-left.article-tool.pdf.d-flex.align-items-center')
                           .get_attribute('href'))
            except Exception:
                send_sms(DownloadError(
                    f"Downloading the article with num of {article_num} of the journal {journal_name} was "
                    f"not successful."))

            # TODO WAIT UNTIL DOWNLOADED

            # PARSE THE SCANNED PDF
            parsed_text = ""
            try:
                parsed_text = parser.get_text_with_specs(path_='etc', num_pages=1, font_type=12.00)
                pass
            except Exception:
                # Does not end the iteration but only sends an SMS.
                parse_successfull = False
                send_sms(ParseError(f"Article could not be parsed, journal: {journal_name}, article: {article_num}."))
                break

            # EXTRACTING DATA FROM PARSED TEXT
            author_num = 0


            # UPDATE THE SCANNED ARTICLES LIST IF PARSED
            if parse_successfull:
                update_scanned_articles(url=article_url, is_doi=False, path_=__file__)
                num_successfully_scraped += 1

            driver.execute_script("window.history.go(-1)")
            WebDriverWait(driver, timeout=1).until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')))
    article_num += 1

if ((num_successfully_scraped / len(article_url_list)) * 100) > 80:
    update_scanned_issues(vol_num=recent_volume, issue_num=recent_issue, path_=__file__)
else:
    send_sms((f"Article url does not exist for the {journal_name}, article {article_num}."))

driver.close()
