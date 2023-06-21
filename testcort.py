import json
import time
from common.services.azure.azure_response_extractor import ApiResponseExtractor
from common.services.azure.azure_helper import AzureHelper
from common.helpers.methods.author_data_mapper import associate_authors_data
# header = AzureHelper.analyse_pdf(r'C:\Users\emine\PycharmProjects\Article-Search\common\services\azure\test_pdf33.pdf')
# #
# time.sleep(15)
# #
# response = AzureHelper.get_analysis_results(header, 50)
#
# with open("file.txt", "w", encoding='utf-8') as file:
#     file.write(json.dumps(response["Data"]))

with open("file.txt", "r", encoding='utf-8') as file:
    response = json.loads(file.read())

extractor = ApiResponseExtractor(response["Data"])
#
print(extractor.extract_article_doi())
print(extractor.extract_article_code())
print(extractor.extract_journal_abbreviation())
print(extractor.extract_page_range())
print(extractor.extract_article_year())
print(extractor.extract_volume_issue())
#
# print(extractor.extract_author_names())
# print(extractor.extract_authors_emails())
# print(extractor.extract_author_data())
# print(associate_authors_data(extractor.extract_author_names(), extractor.extract_authors_emails(), extractor.extract_author_data()))
# print("Author names:", extractor.extract_author_names())
# print("Author emails:", extractor.extract_authors_emails())
# print("Author specialities:", extractor.extract_author_data())

