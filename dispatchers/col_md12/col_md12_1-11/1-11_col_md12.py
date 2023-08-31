"""
This dispatcher will run on every Monday midnights. It will run through 00:00 to 07:00
Cron job for the script:

"""
import time
import json
import sys

from common.erorrs import GeneralError
from common.services.send_sms import send_notification
from scrapers.col_md12_scraper import col_md12_scraper

sys.path.append("/home/ubuntu/article-search")

with open('1-11_col_md12_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# Sample Params
# [
#     "Turkish Journal of Physical Medicine and Rehabilitation",
#     "https://www.ftrdergisi.com/archive.php",
#     "col_md12",
#     1,
#     "thursday_1-11_col_md12",
#     "9_turkishjournalofphysicalmedicineandrehabilitation"
# ],

for dergi_params in params_data:
    try:
        time_spent = col_md12_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(600 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of col_md12 scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
