"""
This is the author class
"""


class Author:

    def __init__(self, name=None, country="Türkiye", all_speciality=None, institution=None, faculty=None,
                 department=None, speciality=None, sub_speciality=None, university=None, mail=None,
                 is_correspondace=False):
        self.is_correspondace = is_correspondace
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

    def author_to_text(self):
        print(self.name)
        print(self.all_speciality)

    @classmethod
    def author_to_json(cls, authors):
        author_list = list()
        for author in authors:
            author_dictionary = dict()
            author_dictionary["Name"] = author.name
            author_dictionary["Full Speciality"] = author.all_speciality
            author_dictionary["Is Correspondance?"] = author.is_correspondace
            author_list.append(author_dictionary)
        return author_list
