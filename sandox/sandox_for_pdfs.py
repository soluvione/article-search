"""This is the experimental area for getting the character attributes of the PDFs"""
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_all_elements
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_text_boxes
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_font_details
from common.helpers.methods.pdf_parse_helpers.pdf_parser import get_text_with_specs
from common.helpers.methods.pdf_parse_helpers.pdf_parser import get_text_boxes
import re

pdf = 'ankem2.pdf'
if True:
    # print(print_all_elements(pdf, 1))
    # print(print_text_boxes(pdf, 1))
    uni_string = re.sub('\d', '', get_text_with_specs(pdf, 1, "ABCDEE+Calibri", 9.960000000000036)).strip()
    uni_list = []
    last_index = 0
    mixed_text_bulk = get_text_with_specs(pdf, 2, "ABCDEE+Calibri,Italic", 9.0, True, "ABCDEE+Calibri,BoldItalic", -1,  True,
                              "ABCDEE+Calibri,Bold", 9.960000000000036)

    for i in range(len(uni_string.split())):
        if uni_string.split()[i].isupper():
            if i == len(uni_string.split())-1:
                uni_list.append(uni_string[last_index:])
            else:
                uni_list.append((uni_string[last_index:uni_string.index(uni_string.split()[i])-2]))
                last_index = uni_string.index(uni_string.split()[i])+len(uni_string.split()[i])
    string = get_text_boxes(pdf, 1, 3) + get_text_boxes(pdf, 1, 4)
    string = string[:string.index('-')] + string[string.rindex('-'):]

    temp_string = list(string)
    for i in range(len(temp_string)):
        if temp_string[i].isnumeric() and temp_string[i - 1].isalpha():
            if temp_string[i + 1] != ',':
                temp_string[i + 1] = ','
        if temp_string[i] == ',' and temp_string[i + 1] == ',':
            temp_string[i] = " "

    string = ''.join(temp_string)
    author_list = string.split(',')
    final_author_list = []
    for element in author_list:
        if ':' in element:
            continue
        no_words = True
        for char in element:
            if char.isalpha():
                no_words = False
                break
        if no_words:
            continue
        new_element = author_list[author_list.index(element)].strip()
        new_element = re.sub(r'\n', '', new_element)
        if (new_element[-1].isnumeric() and new_element[-2].isalpha()):
            final_author_list.append(new_element)
            continue
    author_names = []
    author_codes = []
    for element in final_author_list:
        author_names.append(element[:-1])
        author_codes.append((element[-1:]))
    final_author_list_dic = zip(dict())
    references_bulk = get_text_with_specs(pdf,0, "ABCDEE+Calibri", 9.960000000000036)[get_text_with_specs(pdf,0, "ABCDEE+Calibri", 9.960000000000036).index("No financial support was received for the Project"):]
    last_index = 1
    next_index = 2
    references_list = []
    print(references_bulk)
    print(references_bulk[references_bulk.index(f" {8}.")+2].isalpha())
    while True:
        try:
            if next_index < 10 and references_bulk[references_bulk.index(f" {last_index}.")+3].isalpha() and references_bulk[references_bulk.index(f" {next_index}.")+3].isalpha():
                references_list.append(
                    references_bulk[references_bulk.index(f" {last_index}."): references_bulk.index(f" {next_index}.")])
                last_index = next_index
                next_index += 1
            elif next_index >= 10 and references_bulk[references_bulk.index(f" {last_index}.")+4].isalpha() and references_bulk[references_bulk.index(f" {next_index}.")+4].isalpha():
                references_list.append(
                    references_bulk[references_bulk.index(f" {last_index}."): references_bulk.index(f" {next_index}.")])
                last_index = next_index
                next_index += 1
            print(references_list)
            print(last_index,next_index)
        except:
            break
    """
    article_headline = re.sub('[\n{1,4}*]', '', get_text_boxes(pdf,1,0)) = Article Headline
    article_type = get_text_boxes(pdf,1,1)[:get_text_boxxes(pdf,1,1).index("/")]
    article_name = re.sub('[\n{1,4}*]', '', get_text_boxes(pdf,1,2))
    abstract_tr = mixed_text_bulk[mixed_text_bulk.index("ÖZ")+2:mixed_text_bulk.index("Anahtar")].strip()
    try:
        abstract_eng = mixed_text_bulk[mixed_text_bulk.index("SUMMARY"):mixed_text_bulk.index("Keywords")][8:].strip()
    except:
        abstract_eng = mixed_text_bulk[mixed_text_bulk.index("ABSTRACT"):mixed_text_bulk.index("Keywords")][9:].strip()
    try:
        keywords_tr = mixed_text_bulk[mixed_text_bulk.index("Anahtar"):mixed_text_bulk.index("SUMMARY")][18:].strip().split(',')
    except Exception:
        keywords_tr = mixed_text_bulk[mixed_text_bulk.index("Anahtar"):mixed_text_bulk.index("ABSTRACT")][18:].strip().split(',')
    keywords_eng = mixed_text_bulk[mixed_text_bulk.index("Keywords:")+9: mixed_text_bulk.index("GİRİŞ")].strip().split(',')
    """
