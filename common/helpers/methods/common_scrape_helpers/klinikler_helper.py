import re
from classes.author import Author
from common.errors import GeneralError
from common.services.send_notification import send_notification
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException


# Create a function for pairing the author names and specialities on the basis of the last small letter character of
# each name and the small letter at the beginning of the specialities. Function consumes two lists of author names
# and specialities and returns a list of paired authors.

def pair_authors(author_names_list, author_specialities):
    """
    Function for pairing the author names and specialities on the basis of the last small letter character of each name and the small letter at the beginning of the specialities
    :param author_names_list:
    :param author_specialities:
    :return:
    """
    paired_authors = []
    try:
        for i in range(len(author_names_list)):
            author = Author()
            # remove small letters at the end of the author name until encountering a capitalized letter and commas from author names
            author.name = re.sub(r"[a-z,]+$", '', author_names_list[i])
            # author names end with capitalized letters followed by one or two small letters. get the last small letter character of the author name
            last_small_letter = author_names_list[i].strip()[-1]
            # find the speciality beginning with the same small letter
            for speciality in author_specialities:
                if speciality.startswith(last_small_letter):
                    author.all_speciality = speciality[1:]
                    break
            author.is_correspondence = False
            author.mail = None
            paired_authors.append(author)
        return paired_authors
    except Exception as e:
        send_notification(GeneralError(f"Error while pairing authors (pair_authors, klinikler_helper). Error encountered was: {e}"))
        return paired_authors


def format_bulk_data(raw_text, language):
    """
    Function for formatting the bulk text scraped from article page
    :param raw_text: The text body of the article abstract and keywords either in Turkish or English
    :param language: String eng | tr
    :return: String abstract && keywords
    """
    abstract, keywords = None, None
    try:
        abstract = raw_text[raw_text.index('\n'): raw_text.index('Keywords:')].strip() \
            if language == "eng" \
            else raw_text[raw_text.index('\n'): raw_text.index('Anahtar Kelimeler:')].strip()
        keywords = raw_text[raw_text.index('Keywords:') + 9:].strip().split(";") \
            if language == "eng" \
            else raw_text[raw_text.index('Anahtar Kelimeler:') + 19:].strip().split(";")
        keywords = [keyword.strip() for keyword in keywords]
        return abstract, keywords

    except Exception as e:
        send_notification(GeneralError(f"Error encountered while formatting TK no ref bulk data ("
                                       f"format_bulk_data, klinikler_helper). Error encountered was: {e, type(e).__name__}"))
        return abstract, keywords


def get_article_titles(article_element):
    turkish_title, english_title = None, None
    try:
        turkish_title = article_element.find_element(By.CLASS_NAME, 'nameMain').get_attribute('innerHTML')
        english_title = article_element.find_element(By.CLASS_NAME, 'nameSub').get_attribute('innerHTML')
    except Exception as e:
        send_notification(GeneralError(f"Error encountered while formatting TK article titles ("
                                       f"format_bulk_data, klinikler_helper). Error encountered was: {e}"))
    return turkish_title, english_title

def get_page_range(full_reference_text, pdf_scrape_type):
    """
    Function for getting the page range of the article
    :param full_reference_text: The full reference text of the article
    :return: List of page range numbers
    """
    page_range = None
    article_code = None
    article_volume = None
    article_issue = None
    try:
        if pdf_scrape_type == "A_KLNK":
            full_reference_text = full_reference_text[: -1]
            cropped_text = full_reference_text[full_reference_text.rindex('.') + 1:].strip().split('-')
            page_range = [int(page) for page in cropped_text]
            # if the second int in the page_range list is smaller than the first int, then add the 10 times first int's digit to the second int
            if page_range[1] < page_range[0]:
                page_range[1] += page_range[0] // 10 * 10
        else:
            article_code = full_reference_text[full_reference_text.rindex('.') + 1:].strip()
            page_range = full_reference_text[full_reference_text.rindex(':') + 1:].strip()
            page_range = [int(page) for page in page_range.split('-')]  # convert the page range to a list of ints

            article_volume = full_reference_text[full_reference_text.index(';') + 1: full_reference_text.index('(')]
            article_issue = full_reference_text[full_reference_text.index('(') + 1: full_reference_text.index(')')]

            article_volume = int(article_volume)
            article_issue = int(article_issue)
    except Exception as e:
        send_notification(GeneralError(f"Error encountered while getting TK article page range ("
                                       f"get_page_range, klinikler_helper). Error encountered was: {e}"))
    return page_range, article_code, article_volume, article_issue
