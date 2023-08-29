"""
This module provides the body code of the scrapers and whenever a change happens on DOM structure these code
should be updated.

Components are listed in the order they are used, so that they resemble a full working scraper template
"""
import requests
from datetime import datetime
import time
from common.erorrs import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter
from common.services.send_sms import send_notification

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException


def get_to_the_page(driver, start_page_url, journal_name):
    # GET TO THE PAGE
    if requests.head(start_page_url).status_code != 200:
        send_notification(DownServerError(f"Servers of the journal {journal_name} are down."))
        DownServerError(f"Servers of the journal {journal_name} are down.")
    try:
        driver.get(start_page_url)
    except WebDriverException:
        send_notification(ScrapePathError(f"Could not reach the webpage of {journal_name}."))
        raise ScrapePathError(f"Could not reach the webpage of {journal_name}.")


def get_latest_data(driver, journal_name):
    # GET THE DATA ABOUT THE LATEST ISSUE/VOLUME
    try:
        latest_publication_element = driver.find_element(By.CSS_SELECTOR, '.kt-widget-18__item')
        return latest_publication_element
    except NoSuchElementException:
        send_notification(ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down."))
        raise ScrapePathError(f"Could not reach the webpage of{journal_name}. Servers could be down.")


def go_to_issue_page(driver, latest_publication_element, journal_name, recent_volume, recent_issue):
    # GET TO THE ISSUE PAGE
    try:
        driver.get(latest_publication_element.find_element(By.TAG_NAME, 'a').get_attribute('href'))
    except NoSuchElementException:
        send_notification(ScrapePathError(f"Could not retrieve element of the webpage of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve element of the webpage of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")
    time.sleep(1)


def scrape_year_information(driver):
    # SCRAPE YEAR INFORMATION OF THE ISSUE
    try:
        issue_year = driver.find_element(By.CSS_SELECTOR, 'span.kt-widget-12__desc').text.split()[-1]
        return issue_year
    except NoSuchElementException:
        # If for any reason try suite fails, the default year is set to the current year
        # This method will work fine for 99% of the times, will give correct year data
        issue_year = datetime.now().year
        return issue_year


def scrape_article_urls(driver, article_elements, article_url_list, journal_name, recent_volume, recent_issue):
    article_num = 0
    # SCRAPE ARTICLE PAGE URL FROM EACH ELEMENT
    for article in article_elements:
        try:
            article_url = article.find_element(By.CSS_SELECTOR, '.card-title.article-title').get_attribute('href')
            article_url_list.append(article_url)
        except Exception:
            # Does not end the iteration but only sends an SMS.
            send_notification(
                ScrapePathError(f"Article url does not exist for the {journal_name, recent_volume, recent_issue}"
                                f", article {article_num}."))
        article_num += 1


def scrape_article_elements(driver, journal_name, recent_volume, recent_issue):
    # SCRAPE ARTICLE ELEMENTS AS SELENIUM ELEMENTS
    try:
        article_elements = driver.find_elements(By.CSS_SELECTOR, '.card.j-card.article-project-actions.article-card')
        return article_elements
    except Exception:
        send_notification(ScrapePathError(f"Could not retrieve article urls of "
                                          f"{journal_name, recent_volume, recent_issue}. DOM could be changed."))
        raise ScrapePathError(f"Could not retrieve article urls of "
                              f"{journal_name, recent_volume, recent_issue}. DOM could be changed.")


def download_article_pdf(driver, pdf_scrape_type):
    # DOWNLOAD ARTICLE PDF
    try:
        # PDF LINK THAT WHEN DRIVER GETS THERE THE DOWNLOAD STARTS
        driver.get(driver.find_element
                   (By.CSS_SELECTOR, 'a.btn.btn-sm.float-left.article-tool.pdf.d-flex.align-items-center')
                   .get_attribute('href'))
        pdf_to_download_available = True
        return pdf_to_download_available
    except Exception as e:
        if pdf_scrape_type != "A_DRG":
            pass
        else:
            raise e


def define_article_type(driver):
    article_type = identify_article_type(
        driver.find_element(By.CSS_SELECTOR, 'div.kt-portlet__head-title').text, len(driver.find_elements(
            By.CSS_SELECTOR, 'div.article-citations.data-section')))
    return article_type


def get_page_range(driver):
    try:
        article_subtitle_elements = driver.find_elements(By.CSS_SELECTOR, 'span.article-subtitle')
        for element in article_subtitle_elements:
            if element.text:
                article_page_range = element.text.split(',')[-2].strip().split('-')
                article_page_range = [int(page_num) for page_num in article_page_range]
            return article_page_range
    except Exception as e:
        raise e


def get_language_tabs(driver):
    lang_navbar = driver.find_element(By.CSS_SELECTOR,
                                      'ul.nav.nav-tabs.nav-tabs-line.nav-tabs-line-dergipark.nav-tabs-line-3x.nav-tabs-line-right.nav-tabs-bold')
    language_tabs = lang_navbar.find_elements(By.CSS_SELECTOR, '.nav-item')
    return language_tabs


def define_article_language(driver):
    if "Türkçe" in driver.find_element(By.CSS_SELECTOR, 'table.record_properties.table').find_element(
            By.TAG_NAME, 'tr').text:
        article_lang = "TR"
    else:
        article_lang = "ENG"
    return article_lang


def get_single_lang_article_elements(driver):
    article_title_elements = driver.find_elements(By.CSS_SELECTOR, 'h3.article-title')
    keywords_elements = driver.find_elements(By.CSS_SELECTOR, 'div.article-keywords.data-section')
    abstract_elements = driver.find_elements(By.CSS_SELECTOR, 'div.article-abstract.data-section')
    button = driver.find_element(By.XPATH, '//*[@id="show-reference"]')
    return article_title_elements, keywords_elements, abstract_elements, button


def get_reference_elements(driver):
    reference_list_elements = driver.find_elements(
        By.CSS_SELECTOR, 'div.article-citations.data-section')
    return reference_list_elements


def get_turkish_data(driver, language_tabs):
    """
    This the part where
    :param driver: Webdriver
    :param language_tabs: Tabs CSS item
    :return: Returns Turkish abstract and Turkish article title
    """
    # GO TO THE TURKISH TAB
    language_tabs[0].click()
    time.sleep(0.7)
    tr_article_element = driver.find_element(By.ID, 'article_tr')
    article_title_tr = tr_article_element.find_element(By.CSS_SELECTOR, '.article-title').get_attribute(
        'innerText').strip()
    abstract_tr = abstract_formatter(tr_article_element.find_element(By.CSS_SELECTOR,
                                                                     'div.article-abstract.data-section') \
                                     .find_element(By.TAG_NAME, 'p').get_attribute('innerText'), "tr")
    return tr_article_element, article_title_tr, abstract_tr


def get_english_data(driver):
    eng_article_element = driver.find_element(By.ID, 'article_en')
    article_title_eng = eng_article_element.find_element(By.CSS_SELECTOR,
                                                         'h3.article-title').get_attribute(
        'innerText').strip()
    abstract_eng_element = \
        eng_article_element.find_element(By.CSS_SELECTOR,
                                         'div.article-abstract.data-section') \
            .find_elements(By.TAG_NAME, 'p')
    return eng_article_element, article_title_eng, abstract_eng_element


def get_multiple_lang_article_keywords(article_element):
    return article_element.find_element(By.CSS_SELECTOR, 'div.article-keywords.data-section')


def get_multiple_lang_article_refs(eng_article_element):
    reference_list_elements = eng_article_element.find_element(
        By.CSS_SELECTOR, 'div.article-citations.data-section').find_elements(By.TAG_NAME, 'li')
    return reference_list_elements


def get_author_elements(driver):
    return driver.find_elements(By.CSS_SELECTOR, "p[id*='author']")


def get_doi(driver):
    return driver.find_element(By.CSS_SELECTOR, 'a.doi-link').get_attribute('innerText')
