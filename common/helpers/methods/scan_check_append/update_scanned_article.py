"""
This module updates the local scanned articles json file and appends the newly scanned article to the existing json file
"""
import json
from pathlib import Path
import os


def update_scanned_articles(doi=None, url=None, is_doi=True, path_="") -> bool:
    """
    It is very important to have the local scanned_article_dois.json file.
    :param doi: Unique DOI of the article
    :param url: URL of the article
    :param is_doi: If True, then the function will update the local json records, and conversely, URL file if passed False.
    :param path_: PATH value of the script, "__file__" should be used
    :return: Returns True if updating was successful
    """
    if is_doi:
        scanned_articles_path = os.path.join(path_, "scanned_article_dois.json")
        try:
            json_file = open(scanned_articles_path, encoding='utf-8')
            scanned_articles_list = json.load(json_file)
            json_file.close()

            if doi in scanned_articles_list:
                return False
            else:
                scanned_articles_list.append(doi)
                with open(scanned_articles_path, 'w') as json_file:
                    json_file.write(json.dumps(scanned_articles_list, indent=4))

                return True

        except FileNotFoundError:
            print("Could not update the scanned article doi records!")
            return False

    else:
        try:
            scanned_articles_path = os.path.join(path_, "scanned_article_urls.json")
            json_file = open(scanned_articles_path, encoding='utf-8')
            scanned_articles_list = json.load(json_file)
            json_file.close()

            if url in scanned_articles_list:
                return False
            else:
                scanned_articles_list.append(url)
                with open(scanned_articles_path, 'w') as json_file:
                    json_file.write(json.dumps(scanned_articles_list, indent=4))
                return True

        except FileNotFoundError:
            print("Could not update the scanned article doi records!")
            return False
