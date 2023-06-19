# where to save part
"""
import os
import zipfile

# Define the base path
base_path = os.path.join('path', 'to', 'your', 'directory')  # Put your actual path here

# Save the result from Adobe Extract Text API as usual
zip_filename = "ExtractTextInfoFromPDF.zip"
result.save_as(os.path.join(base_path, "output", zip_filename))

# Specify the zip file name
zip_file = os.path.join(base_path, "output", zip_filename)

# Create a ZipFile Object
with zipfile.ZipFile(zip_file, 'r') as zip_ref:
    # Extract all the contents of the zip file in the same directory
    zip_ref.extractall(os.path.join(base_path, "output"))

"""

def no_timeout():
    import logging
    import os.path

    from adobe.pdfservices.operation.auth.credentials import Credentials
    from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
    from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions
    from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
    from adobe.pdfservices.operation.execution_context import ExecutionContext
    from adobe.pdfservices.operation.io.file_ref import FileRef
    from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation

    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

    try:
        # get base path.
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Initial setup, create credentials instance.
        credentials = Credentials.service_account_credentials_builder() \
            .from_file(base_path + "/pdfservices-api-credentials.json") \
            .build()

        # Create an ExecutionContext using credentials and create a new operation instance.
        execution_context = ExecutionContext.create(credentials)
        extract_pdf_operation = ExtractPDFOperation.create_new()

        # Set operation input from a source file.
        source = FileRef.create_from_local_file(base_path + "/resources/test.txt")
        extract_pdf_operation.set_input(source)

        # Build ExtractPDF options and set them into the operation
        extract_pdf_options: ExtractPDFOptions = ExtractPDFOptions.builder() \
            .with_element_to_extract(ExtractElementType.TEXT) \
            .build()
        extract_pdf_operation.set_options(extract_pdf_options)

        # Execute the operation.
        result: FileRef = extract_pdf_operation.execute(execution_context)

        # Save the result to the specified location.
        result.save_as(base_path + "/output/ExtractTextInfoFromPDF.zip")
    except (ServiceApiException, ServiceUsageException, SdkException):
        logging.exception("Exception encountered while executing operation")

def with_timeout():
    import logging
    import os.path

    from adobe.pdfservices.operation.auth.credentials import Credentials
    from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, \
        SdkException
    from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions
    from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
    from adobe.pdfservices.operation.execution_context import ExecutionContext
    from adobe.pdfservices.operation.io.file_ref import FileRef
    from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation

    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

    try:
        # get base path.
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Initial setup, create credentials instance.
        credentials = Credentials.service_account_credentials_builder() \
            .from_file(base_path + "/pdfservices-api-credentials.json") \
            .build()

        # Create an ExecutionContext using credentials and create a new operation instance.
        execution_context = ExecutionContext.create(credentials)
        extract_pdf_operation = ExtractPDFOperation.create_new()

        # Set operation input from a source file.
        source = FileRef.create_from_local_file(base_path + "/resources/test.txt")
        extract_pdf_operation.set_input(source)

        # Build ExtractPDF options and set them into the operation
        extract_pdf_options: ExtractPDFOptions = ExtractPDFOptions.builder() \
            .with_element_to_extract(ExtractElementType.TEXT) \
            .build()
        extract_pdf_operation.set_options(extract_pdf_options)

        # Execute the operation.
        result: FileRef = extract_pdf_operation.execute(execution_context)

        # Save the result to the specified location.
        result.save_as(base_path + "/output/ExtractTextInfoFromPDF.zip")
    except (ServiceApiException, ServiceUsageException, SdkException):
        logging.exception("Exception encountered while executing operation")

def get_data():
    import json

    # assuming data_str is the string of your JSON
    with open('structuredData.json', 'r', encoding='utf-8') as file:
        data = json.loads(file.read())

    result = [element['Text'] for element in data['elements'] if element['Path'].endswith('LBody')]

    print(json.dumps(result, indent=4, ensure_ascii=False))
