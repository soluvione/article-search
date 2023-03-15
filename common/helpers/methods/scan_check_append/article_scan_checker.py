"""
This module has 2 functions to be used for checking whether the passed article is scanned, by either using
URL of DOI information. Depending on the ease of use, either of the functions can be used for verification and
will work the same way.
"""

import json
from pathlib import Path


def is_article_scanned_doi(doi: str, path_: str) -> bool:
    """
    It is very important to name scanned articles doi json as scanned_article_dois.json in the same directory.
    :param doi: DOI of the journal
    :param path_: PATH value of the script, "__file__" should be used
    :return: Returns a boolean value, True if article has already been scanned
    """
    try:
        scanned_articles_path = Path(path_).parent / "scanned_article_dois.json"
        json_file = open(scanned_articles_path, encoding='utf-8')
        scanned_articles_list = json.load(json_file)
        is_scanned = False
        json_file.close()

        for element in scanned_articles_list:
            if element == doi:
                is_scanned = True
                return is_scanned

        return is_scanned

    except FileNotFoundError:
        raise Exception("Scanned articles doi file does not exist!")


def is_article_scanned_url(url: str, path_: str) -> bool:
    """
    It is very important to name scanned article urls json as scanned_article_urls.json in the same directory.
    :param url: URL value of the article page. The unique page of the article should be used
    :param path_: PATH value of the script, "__file__" should be used
    :return: Returns a boolean value, True if article has already been scanned
    """
    try:
        scanned_articles_path = Path(path_).parent / "scanned_article_urls.json"
        json_file = open(scanned_articles_path, encoding='utf-8')
        scanned_articles_list = json.load(json_file)
        is_scanned = False
        json_file.close()

        for element in scanned_articles_list:
            if element == url:
                is_scanned = True
                return is_scanned

        return is_scanned

    except FileNotFoundError:
        raise Exception("Scanned articles url file does not exist!")
