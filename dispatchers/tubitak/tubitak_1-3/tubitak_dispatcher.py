"""
This dispatcher will run on every Monday midnights. It will run through 00:00 to 07:00
Cron job for the script:

"""
import time
import json

from common.erorrs import GeneralError
from common.services.send_sms import send_notification
from scrapers.tubitak_scraper import tubitak_scraper

with open('tubitak_1-3_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference
# Sample params:
# [
#     "Turkish Journal of Medical Sciences",
#     "journals.tubitak.gov.tr/medical",
#     "tubitak",
#     1,
#     "sunday_1-3_tubitak",
#     "1_turkishjournalofmedicalsciences"
# ],

for dergi_params in params_data:
    try:
        time_spent = tubitak_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(1)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of tubitak scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
