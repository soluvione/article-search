"""
This module includes the functions related to splitting PDFs
"""
from pypdf import PdfWriter, PdfReader
from pathlib import Path


def crop_pages(pdf_path: str, num_pages=1) -> str:
    parent_path = Path(pdf_path).parent.absolute()

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    if num_pages == 1:
        writer.add_page(reader.pages[0])
    else:
        for i in range(0, num_pages):
            writer.add_page(reader.pages[i])

    # Write split pdf to one_page.pdf
    with open(str(parent_path) + rf"\{num_pages}_page.pdf", "wb") as pdf:
        writer.write(pdf)

    one_page_pdf_path = str(parent_path) + rf"\{num_pages}_page.pdf"

    return one_page_pdf_path


def split_in_half(pdf_path: str) -> str:
    parent_path = Path(pdf_path).parent.absolute()

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    starting_page = len(reader.pages) // 2
    for i in range(starting_page, len(reader.pages)):
        writer.add_page(reader.pages[i])
    # Write split pdf to split.pdf
    with open(str(parent_path) + r"\split.pdf", "wb") as pdf:
        writer.write(pdf)

    split_pdf_path = str(parent_path) + r"\split.pdf"

    return split_pdf_path