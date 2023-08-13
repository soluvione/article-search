"""
This module contains the necessary helper functions for parsing PDF files and acquiring raw PDF elements from it.
"""

from pdfminer.high_level import extract_text
from pdfminer.high_level import extract_text_to_fp
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams
from pdfminer.layout import LTTextContainer, LTChar, LTTextBox


def print_all_elements(path_=None, num_pages=0):
    """
   For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed
   :param path_: PATH to the file
   :param num_pages: Starts indexing at 1, entering 0 will return all papers
   :return: Nothing. Only prints pdf elements.
   """
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            print(element)


def print_text_boxes(path_=None, num_pages=0, get_only_text=False):
    """
    For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed
    :param path_: PATH to the file
    :param num_pages: Starts indexing at 1, entering 0 will return all papers
    :param get_only_text: If False will print text box element with details, else will only print texts of text boxes
    :return: Nothing. Only prints pdf elements or their text values.
    """
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                if get_only_text:
                    print(element.get_text())
                else:
                    print(element)


def get_text_boxes(path_=None, num_pages=0, text_box_num=-1):
    """
    :param path_: PATH to the file
    :param num_pages: Starts indexing at 0, entering -1 will return all papers
    :param text_box_num: Which textbox desired to return
    :return: Returns a list of textboxes
    """
    tbox_list = []
    for page_layout in extract_pages(path_, maxpages=num_pages):
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                tbox_list.append(element.get_text())
    if text_box_num != -1:
        return tbox_list[text_box_num]
    else:
        return tbox_list


def print_font_details(path_=None, num_pages=0, get_font=True, get_size=True, get_char=True):
    """
    For the num_pages values, index starts with 1, if 0 is passed then all pages will be displayed
    :param path_: PATH to the file
    :param num_pages: Starts indexing at 1, entering 0 will return all papers
    :param get_font: If True, will print font type of each character
    :param get_size: If True, will print font size of each character
    :param get_char: If True, will print the text value of character
    :return: Nothing. Only prints characters' and their font types & sizes
    """
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


def get_text_with_specs(path_=None, num_pages=0, font1_type=None, font1_size=-1.00, two_fonts=False, font2_type=None, font2_size=-1, three_fonts=False, font3_type=None, font3_size=-1):
    """
    If you want all words with specific font then only enter font_type
    If you want all words with specific font size then only enter None for third arg and enter your font size for the fourth
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
                            if font1_size == -1.00:
                                if font1_type is None:
                                    return_string += character.get_text()
                                elif font1_type == character.fontname:
                                    return_string += character.get_text()
                            else:
                                if font1_type is None and round(character.size, 3) == round(font1_size, 3):
                                    return_string += character.get_text()
                                elif font1_type is not None and font1_type == character.fontname and \
                                        round(character.size, 3) == round(font1_size, 3):
                                    return_string += character.get_text()
                            if two_fonts:
                                if font2_size == -1.00:
                                    if font2_type is None:
                                        return_string += character.get_text()
                                    elif font2_type == character.fontname:
                                        return_string += character.get_text()
                                else:
                                    if font2_type is None and round(character.size, 3) == round(font2_size, 3):
                                        return_string += character.get_text()
                                    elif font2_type is not None and font2_type == character.fontname and \
                                            round(character.size, 3) == round(font2_size, 3):
                                        return_string += character.get_text()
                            if three_fonts:
                                if font3_size == -1.00:
                                    if font3_type is None:
                                        return_string += character.get_text()
                                    elif font3_type == character.fontname:
                                        return_string += character.get_text()
                                else:
                                    if font3_type is None and round(character.size, 3) == round(font3_size, 3):
                                        return_string += character.get_text()
                                    elif font3_type is not None and font3_type == character.fontname and \
                                            round(character.size, 3) == round(font3_size, 3):
                                        return_string += character.get_text()

    return return_string


if __name__ == '__main__':
    print_all_elements(r"C:\Users\emine\Downloads\2020TUSdonem1_TTBT-3-12.pdf", 0)
