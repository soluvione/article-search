import json
import requests
from common.services.send_sms import send_notification


class TKServiceWorker:
    def __init__(self):
        with open("tk_api_config.json", "r") as config_file:
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

            return 1  # TODO can return the response value of the real response
        except Exception as e:
            send_notification(
                f"An error occured while sending the formatted data to TK backend (send_data, tk_service.py). "
                f"Error encountered was: {e}")
            return e

    def test_send_data(self, article_data: dict):
        try:
            url_endpoint = self.__url_endpoint
            headers = self.__headers
            body = json.dumps(article_data)

            response = requests.post(url_endpoint, headers=headers, data=body)
            status = response.json()["success"]

            print(response.json())
        except Exception as e:
            print(e)

# Integration Test
if __name__ == "__main__":
    worker = TKServiceWorker()
    with open (r"C:\Users\BT-EMIN\Desktop\Article-Search-20230818T053035Z-001\Article-Search\Ayşe Hanım\jsons\2_anestezidergisi.json", "r", encoding="utf-8") as file:
        test_data = json.loads(file.read())
    worker.test_send_data(test_data)
