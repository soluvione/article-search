import time
from scrapers.dergipark_scraper import dergipark_scraper

# journal_name, start_page_url, pages_to_send, pdf_scrape_type, parent_type, file_reference
dergi_args_list = [
    ["Genel Sağlık Bilimleri Dergisi", "https://dergipark.org.tr/tr/pub/jgehes", 1, "A_DRG", "foo", "bar"],
    ["Genel Bağımlı Dergisi", "https://dergipark.org.tr/tr/pub/bagimli", 1, "A_DRG", "foo", "bar"],
    # ...
]
dergi_list = None

for dergi_args in dergi_args_list:
    time_spent = dergipark_scraper(*dergi_args)
    if time_spent <= 300:
        time.sleep(300 - time_spent)
    else:
        time.sleep(5)
