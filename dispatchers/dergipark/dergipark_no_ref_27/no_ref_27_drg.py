"""
This dispatcher will run on every Wednesday midnights. It will run through 00:00 to 02:30
Cron job for the script:

"""
import time
import json
import sys
# Needed to append this path for the packages to work as expected
sys.path.append("/home/ubuntu/article-search")

from common.errors import GeneralError
from common.services.send_notification import send_notification
from scrapers.dergipark_scraper import dergipark_scraper

with open('no_ref27_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pages_to_send, pdf_scrape_type, parent_type, file_reference
# Sample params:
# [
#         "Anadolu Çevre ve Hayvan Bilimleri Dergisi (AÇEH)",
#         "https://dergipark.org.tr/tr/pub/jaes",
#         "A_DRG & R",
#         1,
#         "monday_first80_drg",
#         "16_anadoluevrevehayvanbilimleridergisi(aeh)"
# ],

for dergi_params in params_data:
    try:
        time_spent = dergipark_scraper(*dergi_params)
        if time_spent <= 300:
            time.sleep(300 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of Dergipark scraper with journal name: {}, Error:{}.
                **************************************************""".format(dergi_params[0], e)))
        pass
