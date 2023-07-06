"""
This is the author class
"""


class Author:

    def __init__(self, name=None, country="Türkiye", all_speciality=None, institution=None, faculty=None,
                 department=None, speciality=None, sub_speciality=None, university=None, mail=None,
                 is_correspondence=False):
        self.is_correspondence = is_correspondence
        self.name = name
        self.country = country
        self.all_speciality = all_speciality
        self.institution = institution
        self.faculty = faculty
        self.department = department
        self.speciality = speciality
        self.sub_speciality = sub_speciality
        self.university = university
        self.mail = mail

    def __repr__(self):
        return f"Author(name='{self.name}', all_speciality={self.all_speciality}, " \
               f"is_correspondence={self.is_correspondence}, mail={self.mail})"

    def author_to_text(self):
        print(self.name)
        print(self.all_speciality)

    @classmethod
    def author_to_dict(cls, authors):
        author_list = list()
        for author in authors:
            author_dictionary = dict()
            author_dictionary["name"] = author.name
            author_dictionary["fullSpeciality"] = author.all_speciality
            author_dictionary["isCorrespondence"] = author.is_correspondence
            author_dictionary["email"] = author.mail
            author_list.append(author_dictionary)
        return author_list
