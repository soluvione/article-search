"""This is the experimental area for getting the character attributes of the PDFs"""
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_all_elements
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_text_boxes
from common.helpers.methods.pdf_parse_helpers.pdf_parser import print_font_details
from common.helpers.methods.pdf_parse_helpers.pdf_parser import get_text_with_specs
from common.helpers.methods.pdf_parse_helpers.pdf_parser import get_text_boxes
import re

pdf = 'cocuksagligihemsireligiozel8-3-1.pdf'
print_text_boxes(pdf,0)