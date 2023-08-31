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
from scrapers.aves_scraper import aves_scraper

with open('1-16_aves_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference
# Sample params:
# [
#     "Acta Veterinaria Eurasia",
#     "www.actavet.org",
#     "aves",
#     1,
#     "wednesday_1-16_aves",
#     "2_actaveterinariaeurasia"
# ],

for dergi_params in params_data:
    try:
        time_spent = aves_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(600 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of aves scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
