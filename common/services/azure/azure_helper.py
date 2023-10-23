"""
This module contains Azure functions to send requests
"""
import time
import requests
import base64
import json
from common.enums import AzureResponse
from common.errors import GeneralError
from common.services.azure.azure_response_extractor import ApiResponseExtractor
from common.constants import azure_analyse_pdf_url, azure_tk_analyse_pdf_url, subscription_key
from common.helpers.methods.author_data_mapper import associate_authors_data
from common.services.send_notification import send_notification


class AzureHelper:
    def __init__(self):
        pass

    @classmethod
    def analyse_pdf(cls, pdf_path: str, is_tk=False) -> str:
        """

        :param is_tk: Whether if the analyse function will send a TK journal, if so will use different model
        :param pdf_path: Important! This must be an absolute path otherwise will cause errors!
        :return: Returns the operation-header that will be used for fetching the results later
        """
        try:
            send_pdf_response = None
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
                azure_analyse_pdf_url
                if not is_tk
                else azure_tk_analyse_pdf_url,
                params=params,
                headers=headers,
                data=json_payload,
            )

            try:
                return send_pdf_response.headers['Operation-Location']
            except Exception as e:
                if isinstance(send_pdf_response, requests.Response):
                    send_notification(GeneralError(f"Did not receive operation header in the first azure query ("
                                                   f"analyse_pdf, azure_helper.py). Error encountered: {e}. The body of "
                                                   f"response: {send_pdf_response.json()}"))
                else:
                    send_notification(GeneralError(f"Did not receive operation header in the first azure query ("
                                                   f"analyse_pdf, azure_helper.py). Error encountered: {e}."))

                return ""
        except Exception as e:
            send_notification(GeneralError(f"General error in the first Azure API query ("
                                           f"analyse_pdf, azure_helper.py). Error encountered: {e}"))
            return ""

    @classmethod
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
        get_results_response = None
        try:
            get_results_response = requests.get(operation_location, headers=get_results_header)

            if get_results_response.json()["status"] == "succeeded":
                is_finished = True
            while time_past < timeout and not is_finished:
                time.sleep(14)
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
        except Exception as e:
            if get_results_response:
                send_notification(GeneralError(f"General error in the second Azure API query ("
                                               f"get_analysis_results, azure_helper.py). Error encountered: {e}. The body"
                                               f"of the response: {get_results_response.json()}"))
            else:
                send_notification(GeneralError(f"General error in the second Azure API query ("
                                               f"get_analysis_results, azure_helper.py). Error encountered: {e}"))

            response_dictionary["Result"] = AzureResponse.FAILURE.value
            return response_dictionary

    @classmethod
    def format_general_azure_data(cls, azure_data, correspondence_name=None):
        """
        Whether we use the following data, the extractor will extract these and return if present in the pdf.
        Sample article_data return:
        {
        "journal_names": str,
        "journal_abbv": str,
        "doi": str,
        "article_code": str,
        "article_year": int,
        "article_vol": int,
        "article_issue": int,
        "article_page_range": [int, int],
        "article_title": {"TR": str, "ENG": str},
        "article_abstracts": {"TR": str, "ENG": str},
        "article_keywords": {"TR": [str, str], "ENG": [str, str]},
        "article_authors": [author, author],
        }
        :param correspondence_name: None or name of the correspondence author acquired from Dergipark
        :param azure_data: Azure data is the response body, which is the value of the "data" key of response body
        :return: This method returns the article data dictionary.
        """
        data_extractor = ApiResponseExtractor(azure_data)
        try:
            # AUTHOR PART
            # This part is responsible from pairing the extracted author names, emails and author data.
            # After the execution of the called methods, we end up with a dictionary of author objects.
            author_names = data_extractor.extract_author_names()
            author_emails = data_extractor.extract_authors_emails()
            author_data = data_extractor.extract_author_data()
            # Author matcher does the pairing within the method
            article_authors = associate_authors_data(author_names, author_emails, author_data, correspondence_name)

            azure_extraction_data = {
                "journal_names": data_extractor.extract_journal_names(),
                "journal_abbv": data_extractor.extract_journal_abbreviation(),
                "doi": data_extractor.extract_article_doi(),
                "article_code": data_extractor.extract_article_code(),
                "article_year": data_extractor.extract_article_year(),
                "article_vol": data_extractor.extract_volume_issue()["volume"],
                "article_issue": data_extractor.extract_volume_issue()["issue"],
                "article_page_range": data_extractor.extract_page_range(),
                "article_titles": data_extractor.extract_titles(),
                "article_abstracts": data_extractor.extract_abstracts(),
                "article_keywords": data_extractor.extract_keywords(),
                "article_authors": article_authors,
                "correspondence_data": data_extractor.extract_correspondance_data(),
                "emails": author_emails,
            }

            return azure_extraction_data
        except Exception as e:
            send_notification(GeneralError(f"General error while formatting the Azure response data ("
                                           f"format_general_azure_data, azure_helper.py). Error encountered: {e}"))

    @classmethod
    def format_tk_data(cls, tk_data):
        """
        Will consume raw API data and the data will be formatted via TkResponseExtractor,
        Sample article_data return:
        {
            "journal_abbv": str | None,
            "doi": str | None,
            "correspondance_name": str | None,
            "correspondance_email": str | None
        }
        :param tk_data: Raw API data
        :return: Will return formatted article data dictionary
        """
        tk_extraction_data= None
        try:
            data_extractor = ApiResponseExtractor(tk_data["Data"])
            abbreviation = data_extractor.extract_journal_abbreviation(is_tk=True)
            doi = data_extractor.extract_article_doi(is_tk=True)
            author_name = data_extractor.extract_author_names(is_tk=True)
            author_email = data_extractor.extract_authors_emails(is_tk=True)
            tk_extraction_data = {
                "articleCode": abbreviation,
                "articleDOI": doi,
                "correspondance_name": author_name,
                "correspondance_email": author_email
            }
            return tk_extraction_data
        except Exception as e:
            send_notification(GeneralError(f"General error while formatting the Azure TK response data ("
                                           f"format_tk_data, azure_helper.py). Error encountered: {e}"))


# TEST DUMMY RESPONSE
def return_mock_response():
    with open("/home/emin/PycharmProjects/Article-Search/tests/azure_call_data_7june.txt", "r",
              encoding='utf-8') as file:
        fake_response = json.loads(file.read())
        return fake_response


def return_mock_tk_response():
    with open(r"C:\Users\emine\Downloads\tkapitest.txt", "r",
              encoding='utf-8') as file:
        fake_response = json.loads(file.read())
        return fake_response


if __name__ == "__main__":
    # import pprint
    # pprint.pprint(AzureHelper.format_general_azure_data(return_mock_response()))
    # tk_header = AzureHelper.analyse_pdf(r"/home/emin/PycharmProjects/Article-Search/tkapitest.txt", True)
    # response_data = AzureHelper.get_analysis_results(tk_header, 50)
    # with open(r"C:\Users\emine\Downloads\tkapitest.txt", "w",
    #           encoding='utf-8') as file:
    #     json.dump(response_data, file, ensure_ascii=False)
    with open(r"/home/emin/PycharmProjects/Article-Search/tkapitest.txt", "r", encoding='utf-8') as file:
        AzureHelper.format_tk_data(json.loads(file.read()))