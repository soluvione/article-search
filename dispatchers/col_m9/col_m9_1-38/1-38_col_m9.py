"""
This dispatcher will run on every Monday midnights. It will run through 00:00 to 07:00
Cron job for the script:

"""
import time
import json

from common.erorrs import GeneralError
from common.services.send_sms import send_notification
from scrapers.col_m9_scraper import col_m9_scraper

with open('1-38_col_m9_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference
# Sample params:
# [
#     "Ulusal Romatoloji Dergisi",
#     "raeddergisi.org",
#     "col_m9",
#     1,
#     "thursday_1-38_col_m9",
#     "36_ulusalromatolojidergisi"
# ],

for dergi_params in params_data:
    try:
        time_spent = col_m9_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(600 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of col_m9 scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
