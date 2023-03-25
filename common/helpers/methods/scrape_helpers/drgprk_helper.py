import re
from classes.author import Author


def author_converter(author_html: str) -> Author:
    """

    :param author_html: The innerHTML string passed to the function
    :return: Returns an author object
    """
    university_keywords = ["üniversite", "university"]
    is_academia_related = False
    author_name = re.sub(r"&gt;|>", '', author_html[author_html.index('>'): author_html.index('</')])
    author_details = ' '.join(author_html[author_html.index('br>') + 3: author_html.index('orcid') - 20]
                              .split()[:-1])
    auth_details_final = re.sub(r"&gt;|>", '', author_details)
    for keyword in university_keywords:
        if keyword in re.sub('İ', 'i', auth_details_final).lower():
            is_academia_related = True
            break

    new_author = Author()
    new_author.name = author_name
    if is_academia_related:
        try:
            auth_details_final.split(',')[0] = new_author.university
            auth_details_final.split(',')[1] = new_author.faculty
            auth_details_final.split(',')[2] = new_author.department
            auth_details_final.split(',')[3] = new_author.speciality
            auth_details_final.split(',')[4] = new_author.sub_speciality
        except IndexError:
            pass
    else:
        auth_details_final = new_author.institution
    return new_author


def identify_article_type(string: str) -> str:
    """
ARAŞTIRMA MAKALESI
    :param string: The scraped type text from Dergipark issue page
    :return: Returns a string that is selected from the dropdown menu of Atıf Dizini
    """
    if string.lower() == "research article":
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "araştırma makalesi":
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "araştırma makalesı":
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "derleme":
        return "DERLEME"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "olgu sunumu":
        return "OLGU SUNUMU"


def reference_formatter(reference: str) -> str:
    return str
