"""
This module contains Adobe functions to send requests
"""
import json
import pprint
import time
import requests
import logging
import os
import zipfile
from common.erorrs import GeneralError
from common.services.send_sms import send_notification
# 3rd Party imports
from adobe.pdfservices.operation.auth.credentials import Credentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, \
    SdkException
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.execution_context import ExecutionContext
from adobe.pdfservices.operation.io.file_ref import FileRef
from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation


def unzip_results(zip_path):
    """

    :param path_: PATH of the ZIP file, must be absolute path
    :return: Returns the absolute PATH of the extracted JSON file
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all the contents of the zip file in the same directory
            zip_ref.extractall(os.path.dirname(zip_path))
        return os.path.join(os.path.dirname(zip_path), "structuredData.json")
    except Exception as e:
        send_notification(GeneralError(f"Unzip error, error: {e}"))


def format_results(data):
    # result = [element['Text'] for element in data['elements'] if element['Path'].endswith('LBody')]
    keywords = ["References", "Bibliography", "Sources", "Bibliography and references", "Cited Works",
                "Cited References",
                "Works Cited", "Literature", "Citations", "Literature Cited", "Source References", "Resource List",
                "List of References", "Resource References", "Source List", "Bibliographical References",
                "Bibliographic References", "Cited Literature", "Reference List", "Bibliographical Notes",
                "Kaynaklar", "Kaynakça", "Bibliyografya", "Referanslar", "Alıntılar", "Alıntılanan Eserler",
                "Kullanılan Kaynaklar", "Edebiyat", "Alıntılanan Literatür", "Kaynak Listesi", "Alıntılanan Kaynaklar",
                "Kaynak Notları", "Bibliyografik Kaynaklar", "Alıntılanan Edebiyat", "Kaynakça Listesi",
                "Bibliyografik Notlar"]

    keywords = [keyword.lower() for keyword in keywords]
    try:
        # Reverse the list to start search from the end
        reversed_elements = list(reversed(data["elements"]))

        for idx, element in enumerate(reversed_elements):
            if element["Text"].lower() in keywords:
                break
    except KeyError as e:
        print(f"Error finding key in JSON: {e}")

    # Creating new list that has the elements from the keyword element to the end (remembering to reverse back)
    new_elements = list(reversed(reversed_elements[:idx + 1]))

    # Overwriting the old "elements" field with the new list
    data["elements"] = new_elements

    # Converting back to JSON
    new_json = json.dumps(data, indent=4)

    print(new_json)

class AdobeHelper:
    def __init__(self):
        pass

    @classmethod
    def analyse_pdf(cls, pdf_path: str, downloads_folder_path: str) -> str:
        """

        :param pdf_path: Important! This must be an absolute path otherwise will cause errors!
        :return: Returns the operation-header that will be used for fetching the results later.
        """
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

        try:
            # get base path.
            adobe_path = os.path.dirname(os.path.abspath(__file__))

            # Initial setup, create credentials instance.
            credentials = Credentials.service_account_credentials_builder() \
                .from_file(os.path.join(adobe_path, "pdfservices-api-credentials.json")) \
                .build()

            # Create an ExecutionContext using credentials and create a new operation instance.
            execution_context = ExecutionContext.create(credentials)
            extract_pdf_operation = ExtractPDFOperation.create_new()

            # Set operation input from a source file.
            source = FileRef.create_from_local_file(pdf_path)
            extract_pdf_operation.set_input(source)

            # Build ExtractPDF options and set them into the operation
            extract_pdf_options: ExtractPDFOptions = ExtractPDFOptions.builder() \
                .with_element_to_extract(ExtractElementType.TEXT) \
                .build()
            extract_pdf_operation.set_options(extract_pdf_options)

            # Execute the operation.
            result: FileRef = extract_pdf_operation.execute(execution_context)

            zip_path = os.path.join(downloads_folder_path, "adobe_results.zip")
            # Save the result to the specified location.
            result.save_as(zip_path)
            return zip_path
        except (ServiceApiException, ServiceUsageException, SdkException) as e:
            send_notification(GeneralError(f"Adobe API first step error. Error encountered: {e}"))

    @classmethod
    def get_analysis_results(cls, zip_path):
        """
        Timeout should be multiples of 10.
        :param operation_location: The "Operation-Location" value acquired from the response of sending PDF for analysis
        :param timeout: The timeout limit of the operation. How many seconds does the method wait for the analysis to finish.
        :return: Returns response dictionary, Result key for result status and Data key for response body
        """
        try:
            json_path = unzip_results(zip_path)
            with open(json_path, 'r', encoding='utf-8') as json_file:
                raw_data = json.loads(json_file.read())
            format_results(raw_data)
            # pprint.pprint(formatted_data)
        except Exception as e:
            send_notification(GeneralError(f"Adobe API Second phase error. Error encountered: {e}"))
