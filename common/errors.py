"""Exceptions class"""


class Error(Exception):
    """Base class for exceptions in this module"""
    pass


class DownServerError(Error):
    """Exception raised when the server of the page is down, namely the status code isn't 200

        Attributes:
            message -- explanation of the possible reasons of the error
        """
    def __init__(self, message):
        self.message = message


class ScrapePathError(Error):
    """Exception raised when either of the following occurs,
    - Page DOM elements have changed,
    - An unexpected error in the inner workings of the page,

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


class DataPostError(Error):
    """Exception raised when an error regarding posting the data to the backend occurs.

        Attributes:
            message -- explanation of the problem
        """

    def __init__(self, message):
        self.message = message


class GeneralError(Error):
    """Exception raised when a general or vague error occurs.

    Attributes:
        message -- explanation of the problem
    """

    def __init__(self, message):
        self.message = message
