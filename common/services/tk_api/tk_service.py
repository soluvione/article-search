import datetime
import json
import os.path
import requests
import base64
import sys
sys.path.append("/home/ubuntu/article-search")

from common.errors import GeneralError
from common.services.send_notification import send_notification


class TKServiceWorker:
    def __init__(self):
        try:
            with open("./tk_api_config.json", "r") as config_file:
                config_content = json.load(config_file)
        except:
            with open("/home/ubuntu/article-search/common/services/tk_api/tk_api_config.json", "r") as config_file:
                config_content = json.load(config_file)

        self.__url_endpoint = config_content["URL"]
        self.__headers = config_content["HEADERS"]

    def send_data(self, article_data: dict):
        """
        This is the method used for sending the formatted article data to the TK backend. You'd call the worker and this
        method of the worker to send the data
        :param article_data: The formatted article data that has its final form
        :return: Returns 1 if successful else returns an error object
        """
        try:
            url_endpoint = self.__url_endpoint
            headers = self.__headers
            body = json.dumps(article_data)

            response = requests.post(url_endpoint, headers=headers, data=body)
            status: bool = response.json()["success"]
            if not status:
                self.log_errors(response.json())
            return 1  # TODO can return the response value of the real response
        except Exception as e:
            self.log_errors(e)
            send_notification(GeneralError(
                f"An error occurred while sending the formatted data to TK backend (send_data, tk_service.py). "
                f"Error encountered was: {e}"))
            return e

    def test_send_data(self, article_data: dict):
        try:
            url_endpoint = self.__url_endpoint
            headers = self.__headers
            body = json.dumps(article_data)

            response = requests.post(url_endpoint, headers=headers, data=body)
            status = response.json()["success"]
            print("JSON:", response.json())
            print("Response:", response)
            print("Status:", status)
        except Exception as e:
            self.log_errors(e)
            send_notification(GeneralError(
                f"An error occurred while sending the formatted data to TK backend (test_send_data, tk_service.py). "
                f"Error encountered was: {e}"))
            return e

    def encode_base64(self, pdf_path: str) -> str:
        """
        The instance method for encoding and decoding the PDF afterwards
        :param pdf_path: Full PATH of the original PDF
        :return: Returns string representation of PDF
        """
        try:
            with open(pdf_path, "rb") as file:
                pdf_data = file.read()

            pdf_base64 = base64.b64encode(pdf_data).decode()
            return pdf_base64
        except Exception as e:
            return f"PDF Encoding hatası alındı. Lütfen sistem yetkiliniz ile görüşünüz! Hata kodu: {e}"

    def log_errors(self, returned_data):
        """
        If encounter an API error log it onto the local JSON file
        :returned_data: Either an Exception class object or JSON body
        :return: Return nothing
        """
        try:
            file_path = os.path.join(os.path.dirname(__file__), "api_error_logs.json")
            if isinstance(returned_data, Exception):
                data = {"Type": "Error",
                        "Details":
                            {"Error Timestamp": datetime.datetime.now(),
                             "Error Type": str(type(returned_data)),
                             "Error Message": str(returned_data)}}
            else:
                data = {"Type": "Failure",
                        "Details":
                            {"Failure Timestamp": datetime.datetime.now(),
                             "JSON Body": returned_data}}

            with open(file_path, "r") as logs_file:
                existing_logs = json.load(logs_file)

            existing_logs.append(data)

            with open(file_path, "w") as logs_file:
                json.dump(existing_logs, logs_file, default=str, indent=4)
        except Exception as e:
            send_notification(GeneralError(
                f"An error occurred while reading and appending TK API logs (log_errors, tk_service.py). "
                f"Error encountered was: {e}"))

# Integration Test
if __name__ == "__main__":
    worker = TKServiceWorker()
    r"""
    with open(
            r"C:\Users\BT-EMIN\Desktop\Article-Search-20230818T053035Z-001\Article-Search\Ayşe Hanım\jsons\4_experimentalbiomedicalresearch.json",
            "r", encoding="utf-8") as file:
        test_data = json.loads(file.read())
    worker.test_send_data(test_data)
    """
    # Test logs methods
    
    worker.log_errors(GeneralError("An error happened while sending the request!!"))
    """
    worker.send_data({"Corrupted Data Key": "Corrupted Data Value"})
    """
