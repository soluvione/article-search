"""
This dispatcher will run on every Monday midnights. It will run through 00:00 to 07:00
Cron job for the script:

"""
import time
import json

from common.erorrs import GeneralError
from common.services.send_sms import send_notification
from scrapers.sayi_sayfalar_scraper import sayi_sayfalar_scraper

with open('sayi_sayfalar_1-8_params.json', 'r', encoding='utf-8') as f:
    params_data = json.load(f)

# journal_name, start_page_url, pdf_scrape_type, pages_to_send, parent_type, file_reference
# Sample params:
# [
#     "Medical Journal of Islamic World Academy of Sciences",
#     "medicaljournal-ias.org",
#     "sayi_sayfalar",
#     1,
#     "sunday_1-8_sayi_sayfalar",
#     "2_medicaljournalofislamicworldacademyofsciences"
# ],

for dergi_params in params_data:
    try:
        time_spent = sayi_sayfalar_scraper(*dergi_params)
        if time_spent <= 600:
            time.sleep(1)
        else:
            time.sleep(5)
    except Exception as e:
        send_notification(GeneralError("""An error occurred whilst the operations of sayi_sayfalar scraper with journal name: {}, Error:{}.
        **************************************************""".format(dergi_params[0], e)))
        pass
