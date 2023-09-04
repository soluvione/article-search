"""
This module contains Adobe functions to send requests
"""
import json
import logging
import os
import pathlib
import zipfile
from common.errors import GeneralError
from common.services.send_notification import send_notification
from common.helpers.methods.common_scrape_helpers.drgprk_helper import reference_formatter
# 3rd Party imports
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.execution_context import ExecutionContext
from adobe.pdfservices.operation.io.file_ref import FileRef
from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials


def unzip_results(zip_path):
    """

    :param zip_path: PATH of the ZIP file, must be absolute path
    :return: Returns the absolute PATH of the extracted JSON file
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all the contents of the zip file in the same directory
            zip_ref.extractall(os.path.dirname(zip_path))
        return os.path.join(os.path.dirname(zip_path), "structuredData.json")
    except Exception as e:
        send_notification(GeneralError(f"Unzip error, error: {e}"))


def format_results(json_data):
    """
    This function takes the raw data in JSON format and cuts it to include parts after the references
    Afterwards it borrows the function used for Dergipark references formatter
    :param json_data: JSON data of the Adobe API call
    :return: Returns formatted references list. All elements have a leading number attached such as '1.'
    """
    """
    *********************************************************************8888
    **********************************************************************888
    You'll come back. you are looking for ParagraphSpan + P
    
    """
    try:

        keywords = ["References", "Bibliography", "Sources", "Bibliography and references", "Cited Works",
                    "Cited References",
                    "Works Cited", "Literature", "Citations", "Literature Cited", "Source References", "Resource List",
                    "List of References", "Resource References", "Source List", "Bibliographical References",
                    "Bibliographic References", "Cited Literature", "Reference List", "Bibliographical Notes",
                    "KAYNAKLAR ", "Kaynakça", "Bibliyografya", "Referanslar", "Alıntılar", "Alıntılanan Eserler",
                    "Kullanılan Kaynaklar", "Edebiyat", "Alıntılanan Literatür", "Kaynak Listesi",
                    "Alıntılanan Kaynaklar",
                    "Kaynak Notları", "Bibliyografik Kaynaklar", "Alıntılanan Edebiyat", "Kaynakça Listesi",
                    "Bibliyografik Notlar"]

        keywords = [keyword.lower().strip() for keyword in keywords]
        try:
            # Reverse the list to start search from the end
            reversed_elements = list(reversed(json_data["elements"]))
            for idx, element in enumerate(reversed_elements):
                # Checking if "Text" key is in element dictionary
                to_check = None
                if "Text" in element:
                    to_check = element["Text"].lower().strip()
                if to_check in keywords:
                    break
        except KeyError as e:
            print(f"Error finding key in JSON: {e}")

        # Creating new list that has the elements from the keyword element to the end (remembering to reverse back)
        new_elements = list(reversed(reversed_elements[:idx]))
        lbody_count = 0
        p_count = 0
        # Count 'LBody' and 'P' cases in the first 15 elements after the references title
        for sub_element in new_elements[: 20]:
            if "Path" in sub_element:
                if sub_element["Path"].endswith('LBody'):
                    lbody_count += 1
                elif sub_element["Path"].endswith(']') and "/P[" in sub_element["Path"]:
                    p_count += 1

        if lbody_count < p_count:
            result = [element['Text'].strip() for element in new_elements if
                      element["Path"].endswith(']') and "/P[" in element["Path"]]
        else:
            result = [element['Text'].strip() for element in new_elements if element['Path'].endswith('LBody')]
        result = [reference_formatter(reference, False, count) for count, reference in enumerate(result, start=1)]

        return result
    except Exception as e:
        send_notification(GeneralError(
            f"Error while formatting the Adobe API data (format_results, adobe_helper). Error encountered: {e}"))


class AdobeHelper:
    def __init__(self):
        pass

    @classmethod
    def analyse_pdf(cls, pdf_path: str, downloads_folder_path: str) -> str:
        """
        Send PDF to Adobe and get a ZIP file containing the PDF data
        :param downloads_folder_path: The absolute PATH of the downloads folder
        :param pdf_path: Important! This must be an absolute path otherwise will cause errors!
        :return: Returns the PATH of the results ZIP of the Adobe API call
        """
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

        with open(pathlib.Path.joinpath(pathlib.Path(os.path.dirname(os.path.abspath(__file__))), "adobe_credentials.json"), "r") as creds:
            credentials_dict = json.load(creds)
            client_id = credentials_dict["CLIENT_ID"]
            client_secret = credentials_dict["CLIENT_SECRET"]

        try:
            # Initial setup, create credentials instance.
            credentials = ServicePrincipalCredentials(client_id=client_id,
                                                      client_secret=client_secret)

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
        except Exception as e:
            send_notification(
                GeneralError(f"Adobe API First phase error (analyse_pdf, adobe_helper). Error encountered: {e}"))

    @classmethod
    def get_analysis_results(cls, zip_path):
        """
        Timeout should be multiples of 10.
        :param zip_path:
        :return: Returns response dictionary, Result key for result status and Data key for response body
        """
        if not zip_path:
            send_notification(GeneralError(
                f"Adobe API Second phase error (adobe_helper, get_analysis_results). No zip path provided."))
            return None
        try:
            json_path = unzip_results(zip_path)
            with open(json_path, 'r', encoding='utf-8') as json_file:
                raw_data = json.loads(json_file.read())

            return format_results(raw_data)
        except Exception as e:
            send_notification(GeneralError(
                f"Adobe API Second phase error (adobe_helper, get_analysis_results). Error encountered: {e}"))
