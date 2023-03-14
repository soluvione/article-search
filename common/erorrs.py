"""Exceptions class"""
from services import send_sms


class Error(Exception):
    """Base class for exceptions in this module"""
    pass


class ScrapePathError(Error):
    """Exception raised when either of the following occurs,
    - Page DOM elements have changed,
    - An unexpected error in the inner workings of the page,
    - Any server related issues.

    Attributes:
        message -- explanation of the possible reasons of the error
    """

    def __init__(self, message):
        self.message = message


class DownloadError(Error):
    """Exception raised when an error related to the downloads occur.

    Attributes:
        message -- explanation of the problem
    """

    def __init__(self, message):
        self.message = message


class ParseError(Error):
    """Exception raised when an error related to the scraping the PDFs occur.

    Attributes:
        message -- explanation of the problem
    """

    def __init__(self, message):
        self.message = message
