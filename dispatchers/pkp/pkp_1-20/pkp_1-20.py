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
from scrapers.pkp_scraper import pkp_scraper

with open('pkp_1-20_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference
# Sample params:
# [
#     "The Injector",
#     "https://injectormedicaljournal.com/index.php/theinjector/issue/archive",
#     "pkp",
#     1,
#     "thursday_1-20_pkp",
#     "13_theinjector"
# ],

for dergi_params in params_data:
    try:
        time_spent = pkp_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(1)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of pkp scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
