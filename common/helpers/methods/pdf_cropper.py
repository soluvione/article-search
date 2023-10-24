"""
This module includes the functions related to splitting PDFs
"""
from pathlib import Path
import os
from common.errors import GeneralError
from common.services.send_notification import send_notification
from pypdf import PdfWriter, PdfReader

def crop_pages(pdf_path: str, num_pages=1) -> str:
    """

    :param pdf_path: Absolute path of the cropped PDF
    :param num_pages: Number of pages, starting from first page, to be cropped and acquired
    :return: Returns absolute path of the cropped PDF, with a name like xx_page.pdf
    """
    try:
        parent_path = Path(pdf_path).parent.absolute()

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        if num_pages == 1:
            writer.add_page(reader.pages[0])
        else:
            for i in range(0, num_pages):
                writer.add_page(reader.pages[i])

        cropped_pdf_path = os.path.join(str(parent_path), f"{num_pages}_page.pdf")

        # Write split pdf to one_page.pdf
        with open(cropped_pdf_path, "wb") as pdf:
            writer.write(pdf)

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

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        starting_page = len(reader.pages) // 2
        for i in range(starting_page, len(reader.pages)):
            writer.add_page(reader.pages[i])

        split_pdf_path = os.path.join(str(parent_path), "split.pdf")

        # Write split pdf to split.pdf
        with open(split_pdf_path, "wb") as pdf:
            writer.write(pdf)

        return split_pdf_path

    except Exception as e:
        send_notification(e)