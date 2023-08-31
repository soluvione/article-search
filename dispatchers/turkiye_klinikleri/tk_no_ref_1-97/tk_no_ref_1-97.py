"""
This dispatcher will run on every Monday midnights. It will run through 00:00 to 07:00
Cron job for the script:

"""
import time
import json
import sys
# Needed to append this path for the packages to work as expected
sys.path.append("/home/ubuntu/article-search")

from common.erorrs import GeneralError
from common.services.send_sms import send_notification
from scrapers.klinikler_scrapers import klinikler_scraper

with open('tk_no_ref_1-97_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pages_to_send, pdf_scrape_type, parent_type, file_reference
# Sample params:
# [
#     "Türkiye Klinikleri Acil Tıp - Özel Konular",
#     "https://www.turkiyeklinikleri.com/journal/acil-tip-ozel-konular/423/issue-list/tr-index.html",
#     "A_KLNK",
#     1,
#     "saturday_1-97_tk_no_ref",
#     "2_turkiyeklinikleriaciltip-zelkonular"
# ]

for dergi_params in params_data:
    try:
        time_spent = klinikler_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(600 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("An error occured whilt the operations of TK scraper with journal name: {}".format(dergi_params[0])))
        pass
