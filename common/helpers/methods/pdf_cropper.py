"""
This module includes the functions related to splitting PDFs
"""
from pathlib import Path
import os
from common.errors import GeneralError
from common.services.send_notification import send_notification
from pypdf import PdfWriter, PdfReader
import fitz  # PyMuPDF


def crop_pages(pdf_path: str, num_pages=1) -> str:
    """

    :param pdf_path: Absolute path of the cropped PDF
    :param num_pages: Number of pages, starting from first page, to be cropped and acquired
    :return: Returns absolute path of the cropped PDF, with a name like xx_page.pdf
    """
    try:
        parent_path = Path(pdf_path).parent.absolute()
        cropped_pdf_path = os.path.join(str(parent_path), f"{num_pages}_page.pdf")

        try:
            reader = PdfReader(pdf_path, strict=False)
            writer = PdfWriter()
            if num_pages == 1:
                writer.add_page(reader.pages[0])
            else:
                for i in range(0, num_pages):
                    writer.add_page(reader.pages[i])

            # Write split pdf to one_page.pdf
            with open(cropped_pdf_path, "wb") as pdf:
                writer.write(pdf)

            return cropped_pdf_path
        except:
            # Open the source PDF file
            src = fitz.open(pdf_path)

            # New PDF for the selected pages
            new_pdf = fitz.open()

            # Check if the file is not corrupted
            if src.is_pdf:
                if num_pages == 1:
                    new_pdf.insert_pdf(src, from_page=0, to_page=0)
                else:
                    for i in range(num_pages):
                        new_pdf.insert_pdf(src, from_page=i, to_page=i)
            else:
                send_notification(GeneralError(f"Error: Unable to process {pdf_path} (crop_pages, pdf_cropper.py)"))

            new_pdf.save(cropped_pdf_path)
            new_pdf.close()
            src.close()

            return cropped_pdf_path

    except Exception as e:
        send_notification(GeneralError("Pdf Stream error! (crop_pages, pdf_cropper.py)"))


def split_in_half(pdf_path: str) -> str:
    """
    Consumes the absolute path of the target PDF and returns the version of PDF split in half.
    :param pdf_path: Absolute path of target PDF
    :return: Returns absolute path of split PDF
    """
    try:
        parent_path = Path(pdf_path).parent.absolute()
        split_pdf_path = os.path.join(str(parent_path), "split.pdf")

        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            starting_page = len(reader.pages) // 2
            for i in range(starting_page, len(reader.pages)):
                writer.add_page(reader.pages[i])


            # Write split pdf to split.pdf
            with open(split_pdf_path, "wb") as pdf:
                writer.write(pdf)

            return split_pdf_path
        except:
            # Open the source PDF file
            src = fitz.open(pdf_path)
            midpoint = len(src) // 2

            # New PDF for the selected pages
            new_pdf = fitz.open()

            # Check if the file is not corrupted
            if src.is_pdf:
                for page_num in range(midpoint, len(src)):
                    new_pdf.insert_pdf(src, from_page=page_num, to_page=page_num)
            else:
                send_notification(GeneralError(f"Error: Unable to process {pdf_path} (crop_pages, pdf_cropper.py)"))

            new_pdf.save(split_pdf_path)
            new_pdf.close()
            src.close()

            return split_pdf_path

    except Exception as e:
        send_notification(GeneralError("General - An error occurred while splitting a PDF in half! Error: {e}. (split_in_half, pdf_cropper.py)"))