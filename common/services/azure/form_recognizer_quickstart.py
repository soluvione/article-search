import time
import requests
import base64
from azure_data import azure_data_from_dict

import json
# with open("output.txt", 'r', encoding='utf-8') as file:
#     data = json.loads(file.read())
#
# print(azure_data_from_dict(data).analyze_result.documents[0].fields.author_mail.to_dict())

with open("test_pdf1.pdf", "rb") as pdf_file:
    encoded_string = base64.b64encode(pdf_file.read()).decode("utf-8")

headers = {
    'Content-Type': 'application/json',
    'Ocp-Apim-Subscription-Key': '5255bbd274a341a1b8f1bf85c8f3f999',
}
data = f"{{'base64Source': {encoded_string}}}"
payload = {
    "base64Source": encoded_string
}
json_payload = json.dumps(payload)

params = {
    'api-version': '2022-08-31',
}
response = requests.post(
    'https://article-search-recognizer-endpoint.cognitiveservices.azure.com/formrecognizer/documentModels/Author_MailExtractor:analyze',
    params=params,
    headers=headers,
    data=json_payload,
)
operation_header = response.headers['Operation-Location']
print(operation_header)
time.sleep(30)
post_header = {
    'Ocp-Apim-Subscription-Key': '5255bbd274a341a1b8f1bf85c8f3f999',
}

time.sleep(30)
response = requests.get(operation_header, headers=post_header)

with open('output.txt', 'w', encoding='utf-8') as file:
    file.write(json.dumps(response.json(), indent=4, ensure_ascii=False))

print(response.headers, response.json())


"""

https://article-search-recognizer-endpoint.cognitiveservices.azure.com/
https://raw.githubusercontent.com/eminens06/azure_files/main/10.5799-jmid.1265378-3011880-1.pdf
https://article-search-recognizer-endpoint.cognitiveservices.azure.com/formrecognizer/documentModels/Author_MailExtractor/analyzeResults/2a0855eb-dafc-46b7-87c1-4e2acff41f10?api-version=2022-08-31
curl -v -i POST "{endpoint}/formrecognizer/documentModels/{modelID}:analyze?api-version=2022-08-31" -H "Content-Type: application/json" -H "Ocp-Apim-Subscription-Key: {key}" --data-ascii "{'urlSource': '{your-document-url}'}"
5255bbd274a341a1b8f1bf85c8f3f999
"""