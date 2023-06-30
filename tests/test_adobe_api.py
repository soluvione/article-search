import json
import pprint

from common.services.adobe.adobe_helper import AdobeHelper

# AdobeHelper.analyse_pdf(r"/home/emin/Downloads/no_ref_tk_pdf.pdf", "/home/emin/Downloads/")

print(json.dumps(AdobeHelper.get_analysis_results("/home/emin/Downloads/adobe_results.zip"), indent=4, ensure_ascii=False))