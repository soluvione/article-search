"""
This dispatcher will run on every Monday midnights. It will run through 00:00 to 07:00
Cron job for the script:

"""
import time
import json
import sys
# Needed to append this path for the packages to work as expected
sys.path.append("/home/ubuntu/article-search")

from common.errors import GeneralError
from common.services.send_notification import send_notification
from scrapers.unq_tk_scraper import unq_tk_scraper

with open('unq_tk_1-4_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference
# Sample params:
# [
#     "Fiziksel Tıp ve Rehabilitasyon Bilimleri Dergisi",
#     "www.jpmrs.org",
#     "unq_tk",
#     1,
#     "sunday_1-4_unq_tk",
#     "1_fizikseltipverehabilitasyonbilimleridergisi"
# ],

for dergi_params in params_data:
    try:
        time_spent = unq_tk_scraper(*dergi_params)
        if time_spent <= 300:
            time.sleep(1)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of Unique TK scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
