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
from scrapers.karep_scraper import karep_scraper

with open('karep_1-3_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# Sample Params
# [
#     "Düşünen Adam: Psikiyatri ve Nörolojik Bilimler Dergisi",
#     "dusunenadamdergisi.org",
#     "karep",
#     1,
#     "sunday_1-3_karep",
#     "1_dusunenadampsikiyatrivenrolojikbilimlerdergisi"
# ],

for dergi_params in params_data:
    try:
        time_spent = karep_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(600 - time_spent)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of karep scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
