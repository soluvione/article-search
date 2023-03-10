"""
This module contains the necessary helper functions for parsing PDF files and acquiring raw PDF elements from it.
"""

from pdfminer.high_level import extract_text
from pdfminer.high_level import extract_text_to_fp
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams
from pdfminer.layout import LTTextContainer, LTChar, LTTextBox


def display_all_elements(path_=None, num_pages=0):
    """For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed"""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            print(element)


def display_text_boxes(path_=None, num_pages=0, get_only_text=False):
    """For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed"""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                if get_only_text:
                    print(element.get_text())
                else:
                    print(element)


def get_font_details(path_=None, num_pages=0, get_font=True, get_size=True, get_char=True):
    """For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed"""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextBox):
                for text_line in element:
                    for character in text_line:
                        if isinstance(character, LTChar):
                            if get_font:
                                print(character.fontname)
                            if get_size:
                                print(character.size)
                            if get_char:
                                print(character.get_text())


if __name__ == '__main__':
    # display_text_boxes('pdf_example.pdf', 0, True)
    # get_font_details('pdf_example.pdf', 0)
    get_font_details('pdf_example.pdf', 1)
