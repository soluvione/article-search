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
from scrapers.firat_scraper import firat_scraper

with open('firat_1-5_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# Sample Params
# [
#     "Fırat Üniversitesi Sağlık Bilimleri Tıp Dergisi",
#     "tip.fusabil.org",
#     "firat",
#     1,
#     "sunday_1-5_firat",
#     "2_firatuniversitesisalkbilimleritpdergisi"
# ],

for dergi_params in params_data:
    try:
        time_spent = firat_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(600 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of firat scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
