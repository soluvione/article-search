"""
This module contains Adobe functions to send requests
"""
import time
import requests
import base64
import json
from common.enums import AzureResponse
from common.services.azure.azure_response_extractor import ApiResponseExtractor
from common.constants import azure_analyse_pdf_url, subscription_key
from common.helpers.methods.author_data_mapper import associate_authors_data
from common.services.send_sms import send_notification

class AdobeHelper:
    def __init__(self):
        pass

    def analyse_pdf(cls, pdf_path: str) -> str:
        """

        :param pdf_path: Important! This must be an absolute path otherwise will cause errors!
        :return: Returns the operation-header that will be used for fetching the results later.
        """
        try:
            with open(pdf_path, "rb") as pdf_file:
                encoded_string = base64.b64encode(pdf_file.read()).decode("utf-8")

            headers = {
                'Content-Type': 'application/json',
                'Ocp-Apim-Subscription-Key': f'{subscription_key}',
            }
            json_payload = json.dumps({
                "base64Source": encoded_string
            })
            params = {
                'api-version': '2022-08-31',
            }
            send_pdf_response = requests.post(
                azure_analyse_pdf_url,
                params=params,
                headers=headers,
                data=json_payload,
            )

            try:
                return send_pdf_response.headers['Operation-Location']
            except Exception:
                print("send sms: did not receive the operation location from azure send sms response")
                return ""
        except Exception as e:
            print("send sms: general error in first azure query, ", {e})

    def get_analysis_results(cls, operation_location: str, timeout: int):
        """
        Timeout should be multiples of 10.
        :param operation_location: The "Operation-Location" value acquired from the response of sending PDF for analysis
        :param timeout: The timeout limit of the operation. How many seconds does the method wait for the analysis to finish.
        :return: Returns response dictionary, Result key for result status and Data key for response body
        """
        time_past = 0
        is_finished = False
        response_dictionary = {"Result": AzureResponse.RUNNING.value}

        get_results_header = {
            'Ocp-Apim-Subscription-Key': f'{subscription_key}',
        }
        try:
            get_results_response = requests.get(operation_location, headers=get_results_header)

            if get_results_response.json()["status"] == "succeeded":
                is_finished = True
            while time_past < timeout and not is_finished:
                time.sleep(10)
                get_results_response = requests.get(operation_location, headers=get_results_header)
                if get_results_response.json()["status"] == "succeeded":
                    is_finished = True
                time_past += 10
            if is_finished:
                response_dictionary["Result"] = AzureResponse.SUCCESSFUL.value
                response_dictionary["Data"] = get_results_response.json()
            else:
                response_dictionary["Result"] = AzureResponse.FAILURE.value

            return response_dictionary
        except Exception:
            response_dictionary["Result"] = AzureResponse.FAILURE.value
            return response_dictionary
