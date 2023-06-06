"""
This module extracts the following data from Azure API response and leaves the rest:
- Article Title
- Article Abstracts
- Article Keywords
- Article DOI
- Author Names
- Author Emails
- Author Data
"""
import json
import re


def _extract_keywords_from_string(keyword_string):
    """

    :param keyword_string: String of keywords either in Turkish or English
    :return: Returns an array of formatted keywords
    """
    if not keyword_string or not isinstance(keyword_string, str):
        return []

    keyword_string = keyword_string.replace("Key words:", "") \
        .replace("Keywords:", "") \
        .replace("KEYWORDS:", "") \
        .replace("keywords:", "") \
        .replace("Anahtar kelimeler:", "") \
        .replace("Anahtar Kelimeler:", "") \
        .replace("ANAHTAR KELİMELER:", "") \
        .replace("anahtar kelimeler:", "") \
        .strip()

    if not keyword_string:
        return []

    # Split the keywords by comma and remove whitespace
    keywords = [keyword.strip() for keyword in keyword_string.split(",")]

    # Remove the trailing dot from the last keyword
    if keywords:
        keywords[-1] = keywords[-1].strip(".")

    return keywords


def _clean_year(year_string):
    # Consumes a string and returns a four digit number as year
    match = re.search(r'\b\d{4}\b', year_string)
    if match:
        return int(match.group())
    else:
        return None


class ApiResponseExtractor:
    """
    This class assumes that the API response from Azure has only 1 document object in the response body.
    The names must follow the names of the data labels in Azure Form Recognition
    """

    def __init__(self, api_response_json_string):
        """
        Consumes requests body
        :param api_response_json_string: requests response.json()
        """
        if isinstance(api_response_json_string, str):
            try:
                self.api_response = json.loads(api_response_json_string)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string provided to the Azure response extractor")
        elif isinstance(api_response_json_string, dict):
            self.api_response = api_response_json_string
        else:
            raise ValueError("Invalid type for api_response_json_string. Expected str or dict.")

    def extract_titles(self):
        titles = {}
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("title_") and "valueString" in value:
                language = key.split("_")[1]
                titles[language] = value["valueString"]
        return titles

    def extract_abstracts(self):
        abstracts = {}
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("abstract_") and "valueString" in value:
                language = key.split("_")[1]
                abstracts[language] = value["valueString"]
        return abstracts

    def extract_keywords(self):
        keywords = {}
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("keywords_") and "valueString" in value:
                language = key.split("_")[1]
                keywords[language] = _extract_keywords_from_string(value["valueString"])
        return keywords

    def extract_article_doi(self):

        doi = None
        if ("DOI" in self.api_response["analyzeResult"]["documents"][0]["fields"]
                and "valueString" in self.api_response["analyzeResult"]["documents"][0]["fields"][
                    "DOI"]):
            doi = self.api_response["analyzeResult"]["documents"][0]["fields"]["DOI"]["valueString"]
            # print("DOI IS:", doi)
            try:
                doi = doi[doi.index("/10.") + 1:]
            except ValueError:
                return "HATA"
        return doi

    def extract_authors_emails(self):
        emails = []
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("auth_mail") and "valueString" in value:
                emails.append(value["valueString"])
        return emails

    def extract_author_names(self):
        author_names = []
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("author_name") and "valueString" in value:
                author_names.append(value["valueString"])
        return author_names

    def extract_author_data(self):
        author_data = []
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("author_data") and "valueString" in value:
                author_data.append(value["valueString"])
        return author_data

    def extract_journal_names(self):
        journal_names = []
        for key, value in self.api_response["analyzeResult"]["documents"][0]["fields"].items():
            if key.startswith("journal_name") and "valueString" in value:
                journal_names.append(value["valueString"])
        return journal_names

    def extract_article_code(self):
        if "article_code" in self.api_response["analyzeResult"]["documents"][0]["fields"]:
            try:
                return self.api_response["analyzeResult"]["documents"][0]["fields"]["article_code"]["valueString"]
            except KeyError:
                return "HATA"
        else:
            return None

    def extract_correspondance_data(self):
        if "correspondance_data" in self.api_response["analyzeResult"]["documents"][0]["fields"]:
            try:
                return self.api_response["analyzeResult"]["documents"][0]["fields"]["correspondance_data"]["valueString"]
            except KeyError:
                return "HATA"
        else:
            return None

    def extract_journal_abbreviation(self):
        if "journal_abbreviation" in self.api_response["analyzeResult"]["documents"][0]["fields"]:
            try:
                return self.api_response["analyzeResult"]["documents"][0]["fields"]["journal_abbreviation"]["valueString"]
            except KeyError:
                return "HATA"
        else:
            return None

    def extract_article_year(self):
        """
        Returns year value as an integer if possible
        :return: Article year as integer or None
        """
        if "article_year" in self.api_response["analyzeResult"]["documents"][0]["fields"]:
            try:
                return _clean_year(self.api_response["analyzeResult"]["documents"][0]["fields"]["article_year"]["valueString"])
            except Exception:
                return "HATA"
        else:
            return None

    def extract_page_range(self):
        """
        This method consumes a string containing page range data and returns an array of integers that are page range objects
        :return: Page range array as [int, int] or an empty list []
        """
        if "page_range" in self.api_response["analyzeResult"]["documents"][0]["fields"]:
            try:
                page_range_string = self.api_response["analyzeResult"]["documents"][0]["fields"]["page_range"][
                    "valueString"]
                page_range_string = re.findall(r'\d+', page_range_string)
                page_range_numbers = list(map(int, page_range_string))
                page_range_numbers.sort()
                return page_range_numbers[:2]
            except Exception:
                return "HATA"
        else:
            return None

    def extract_volume_issue(self):
        """
        Returns volume and issue values as dictionary if possible
        :return: Article {"volume": None or int, "issue": None or int}
        """
        volume_issue = dict.fromkeys(["volume", "issue"])
        fields = self.api_response["analyzeResult"]["documents"][0]["fields"]
        regex_pattern = r'\b\d{1,2}'
        if "volume" in fields:
            try:
                volume_issue["volume"] = fields["volume"]["valueString"]
                match = re.search(regex_pattern, volume_issue["volume"])
                if match:
                    volume_issue["volume"] = match.group(0)
            except KeyError:
                volume_issue["volume"] = "HATA"

        if "issue" in fields:
            try:
                volume_issue["issue"] = fields["issue"]["valueString"]
                match = re.search(regex_pattern, volume_issue["issue"])
                if match:
                    volume_issue["issue"] = match.group(0)
            except KeyError:
                volume_issue["issue"] = "HATA"

        return volume_issue
