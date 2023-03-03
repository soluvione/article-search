"""
This is an abstract class for journal articles.
This will serve as a scaffolding, abstract class for the prospective subclasses for each journal.
Journal scrapers will create journal objects.
"""
from datetime import date
from datetime import datetime


class JournalArticle:

    def __init__(self, name=None, journal=None, url=None, doi=None, authors=None, references=None, keywords=None,
                 abstract=None, year_published=None):
        """
        This constructor records creation time and day of article object. Passes parameters to the object. If no data
        provided than instantiates the object with null values.
        """
        self.date_acquired = date.today()
        self.date_acquired_wtime = datetime.now()
        self.is_scraped = False
        self.name = name
        self.journal = journal
        self.url = url
        self.doi = doi
        self.authors = authors
        self.references = references
        self.keywords = keywords
        self.abstract = abstract
        self.year_published = year_published

    def data_to_json(self):
        pass