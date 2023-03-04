import json
from pathlib import Path


def is_article_scanned_doi(doi: str, path_: str) -> bool:
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
        raise Exception("Scanned articles doi file does not exist!!")


def is_article_scanned_url(url: str, path_: str) -> bool:
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
        raise Exception("Scanned articles doi file does not exist!!")
