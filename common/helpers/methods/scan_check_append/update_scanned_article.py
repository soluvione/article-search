import json
from pathlib import Path


def update_scanned_articles(doi=None, url=None, is_doi=True, path_=""):
    if is_doi:
        try:
            scanned_articles_path = Path(path_).parent / "scanned_article_dois.json"
            json_file = open(scanned_articles_path, encoding='utf-8')
            scanned_articles_list = json.load(json_file)
            json_file.close()

            if doi in scanned_articles_list:
                print("Doi already in the list")
                return False
            else:
                scanned_articles_list.append(doi)
                with open(scanned_articles_path, 'w') as json_file:
                    json_file.write(json.dumps(scanned_articles_list, indent=4))

                return True

        except FileNotFoundError:
            raise Exception("Could not update the scanned article doi records!")
            return False

    else:
        try:
            scanned_articles_path = Path(path_).parent / "scanned_article_urls.json"
            json_file = open(scanned_articles_path, encoding='utf-8')
            scanned_articles_list = json.load(json_file)
            json_file.close()
            # TODO CHECK THIS CODE
            scanned_articles_list.append(url)

            with open(scanned_articles_path, 'w') as json_file:
                json_file.write(json.dumps(scanned_articles_list, indent=4))

            return True

        except FileNotFoundError:
            raise Exception("Could not update the scanned article doi records!")
            return False
