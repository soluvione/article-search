"""
Journal scrapers will create journal objects.
"""
from datetime import date
from datetime import datetime


class JournalArticle:

    def __init__(self, name=None, journal=None, url=None, article_type=None, doi=None, journal_type=None, authors=None,
                 references=None, keywords=None, header=None, abstract=None, year_published=None):
        """
        This constructor records creation time and day of article object. Passes parameters to the object. If no data
        provided than instantiates the object with null values.
        """
        self.date_acquired = date.today().strftime('%Y-%m-%d')
        self.date_acquired_wtime = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        self.is_scraped = False
        self.name = name
        self.journal = journal
        self.url = url
        self.article_type = article_type
        self.doi = doi
        self.journal_type = journal_type
        self.authors = authors
        self.references = references
        self.keywords = keywords
        self.header = header
        self.abstract = abstract
        self.year_published = year_published

    def data_to_json(self):
        pass