"""
This module contains the necessary helper functions for parsing PDF files and acquiring raw PDF elements from it.
"""

from pdfminer.high_level import extract_text
from pdfminer.high_level import extract_text_to_fp
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams
from pdfminer.layout import LTTextContainer, LTChar, LTTextBox


def print_all_elements(path_=None, num_pages=0):
    """For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed"""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            print(element)


def print_text_boxes(path_=None, num_pages=0, get_only_text=False):
    """For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed"""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                if get_only_text:
                    print(element.get_text())
                else:
                    print(element)


def print_font_details(path_=None, num_pages=0, get_font=True, get_size=True, get_char=True):
    """For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed"""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextBox):
                for text_line in element:
                    for character in text_line:
                        if isinstance(character, LTChar):
                            if get_font:
                                print(character.fontname, " ", end='')
                            if get_size:
                                print(character.size, " ", end='')
                            if get_char:
                                print(character.get_text(), " ", end='')
                            print()


def get_text_with_specs(path_=None, num_pages=0, font_type=None, font_size=-1.00):
    """
    If you want all words with specific font then only enter font_type
    If you want all words with specific font size then only enter None for third arg and enter your number for the fourth
    :param path_: PATH to the file
    :param num_pages: Starts indexing at 1, entering 0 will return all papers
    :param font_type: desired font-type in PDF font format
    :param font_size: desired font size
    :return: A string comprised of desired chars with given size and font-type
    """
    return_string = ""
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextBox):
                for text_line in element:
                    for character in text_line:
                        if isinstance(character, LTChar):
                            if font_size == -1.00:
                                if font_type is None:
                                    return_string += character.get_text()
                                elif font_type == character.fontname:
                                    return_string += character.get_text()
                            else:
                                if font_type is None and round(character.size, 2) == font_size:
                                    return_string += character.get_text()
                                elif font_type is not None and font_type == character.fontname and round(character.size, 2) == font_size:
                                    return_string += character.get_text()

    return return_string


if __name__ == '__main__':
    pass