"""
This is the class for correspondence authors
"""
from classes.author import Author


class CorrespondanceAuthor(Author):
    """This class inherits Author class"""
    def __init__(self, name=None, institution=None, speciality=None, sub_speciality=None, university=None):

        super().__init__(name, institution, speciality, sub_speciality, university)
