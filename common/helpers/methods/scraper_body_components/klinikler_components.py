"""
This module provides the body code of the scrapers and whenever a change happens on DOM structure these code
should be updated.

Components are listed in the order they are used, so that they resemble a full working scraper template
"""
import requests
from datetime import datetime
import time
from common.errors import ScrapePathError, DownloadError, ParseError, GeneralError, DataPostError, DownServerError
from common.helpers.methods.common_scrape_helpers.drgprk_helper import identify_article_type
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter, format_file_name, \
    abstract_formatter
from common.services.send_notification import send_notification

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
