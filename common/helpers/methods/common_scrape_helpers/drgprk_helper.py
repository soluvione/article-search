import re
import os
from classes.author import Author
from common.erorrs import GeneralError
from common.services.send_sms import send_notification


def capitalize_first_occurrence(s):
    # iterate over each character
    for i in range(len(s)):
        # if the character is an alphabet
        if s[i].isalpha():
            # if it is not already uppercase
            if not s[i].isupper():
                # make it uppercase
                s = s[:i] + s[i].upper() + s[i+1:]
            break  # stop after encountering the first alphabet
    return s

def author_converter(author_text: str, author_html: str) -> Author:
    """

    :param author_html: The parsed HTML data of the author object
    :param author_text: The innerText string passed to the function
    :return: Returns an author object
    """
    try:
        author = Author()
        is_foreign_author = False
        split_text = author_text.split('\n')
        if len(split_text) == 4:
            del split_text[-2]
        if split_text[-1] != "Türkiye" and split_text[-1] != "Turkey" and split_text[
            -1] != "Kuzey Kıbrıs Türk Cumhuriyeti":
            is_foreign_author = True
        if "Sorumlu" in split_text[0]:
            author.is_correspondence = True
        if "star-of-life" in author_html:
            author.is_correspondence = True

        # Author last name is always written in capital letters. Same goes for the second last names as well
        author.name = re.sub(r"  Bu kişi benim|&gt;|>", '', split_text[0])
        author.name = re.sub(r" \(Sorumlu Yazar\)", '', author.name)

        if is_foreign_author:
            author.country = "YABANCI"
            author.all_speciality = "YABANCI"
        else:
            author.all_speciality = split_text[1]
        return author
    except Exception as e:
        print(e)


def get_correspondance_name(authors_list):
    for author in authors_list:
        if author.is_correspondence:
            return author.name
    return None


def author_converter1(author_html: str) -> Author:
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


def identify_article_type(string, num_of_references) -> str:
    """
    ARAŞTIRMA MAKALESI
    :param string: The scraped type text from Dergipark issue page
    :return: Returns a string that is selected from the dropdown menu of Atıf Dizini
    """
    # Orijinal Araştırma
    if string.strip().lower() == "research article" or string.strip().lower() == "original article" or string.strip().lower() == "research" or string.strip().lower() == "original research" or string.strip().lower() == "original articles":
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().lower() == "articles":
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "araştırma makalesi":
        return "ORİJİNAL ARAŞTIRMA"
    if "araştırma makale" in string.strip().replace("I", "ı").replace("İ", "i").lower():
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "araştırma makalesı":
        return "ORİJİNAL ARAŞTIRMA"
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "özgün araştırma":
        return "ORİJİNAL ARAŞTIRMA"

    # Klinik Araştırma
    if string.strip() == "KLINIK ARAŞTIRMA" or string.strip() == "Klinik Araştırma" or string.strip() == "KLİNİK ARAŞTIRMA":
        return "KLİNİK ARAŞTIRMA"
    if string.strip().lower() == "original investigation" or string.strip().lower() == "clinical investigation":
        return "KLİNİK ARAŞTIRMA"

    # Derlemeler
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "derleme" or string.strip().replace("I", "ı").replace("İ", "i").lower() == "derleme makalesi":
        return "DERLEME"
    if string.strip().lower() == "review" or string.strip().lower() == "review article":
        return "DERLEME"
    if "review" in string.strip().lower():
        return "DERLEME"
    if "derleme" in string.strip().lower():
        return "DERLEME"

    # Olgu Sunumu
    if string.strip().replace("I", "ı").replace("İ", "i").lower() == "olgu sunumu":
        return "OLGU SUNUMU"
    if string.strip().lower() == "case report" or string.strip().lower() == "case reports":
        return "OLGU SUNUMU"

    # Orijinal Görüntü
    if "orijinal görüntü" in string.strip().lower() or "original image" in string.strip().lower():
        return "ORİJİNAL GÖRÜNTÜ"

    # Diğer
    if string == "DIĞER" and num_of_references == 0:
        return "Diğer"
    if string == "EDITORYAL":
        return "Editoryal"
    if string == "DÜZELTME" and num_of_references > 0:
        return "ORİJİNAL ARAŞTIRMA"
    if "article" in string.strip().lower():
        return "ORİJİNAL ARAŞTIRMA"
    else:
        return "Diğer"


def reference_formatter(reference: str, is_first: bool, count: int) -> str:
    try:
        if is_first:
            reference = re.sub(r"kaynakça|kaynakca|references", "", reference, flags=re.IGNORECASE)
        reference_head = reference[0:18]
        reference_tail = reference[18:]
        reference_head = re.sub(r"referans|reference", "", reference_head, flags=re.IGNORECASE)

        reference_temp = reference_head + reference_tail
        reference_head = reference_temp[:5]
        reference_tail = reference_temp[5:]
        reference_tail = re.sub(r"\s{2,}", "", reference_tail)
        try:
            reference_tail = reference_tail[:re.search(r"doi:|DOI:|https://doi", reference_tail).start()]
        except:
            pass
        reference_head = re.sub(r"[\[\]-_:0-9\.]", "", reference_head)
        reference_head = re.sub(r"\t{1,}", "", reference_head)
        reference_head = re.sub(r"\s{2,}", "", reference_head)
        if reference_head and reference_head[0] == " ":
            reference_head = str(count) + "." + reference_head
        elif not reference_head:
            reference_head = str(count) + ". "
        else:
            reference_head = str(count) + ". " + reference_head
        reference_combined = reference_head + reference_tail

        reference_combined = (reference_combined.split('(<', 1)[0]).replace('[CrossRef]', '').strip()
        reference_combined = capitalize_first_occurrence(reference_combined)
        if reference_combined.endswith("["):
            return reference_combined[:-2]

        return reference_combined
    except Exception as e:
        send_notification(
            GeneralError(f'Error whilst formatting references via dergipark_helper reference_formatter. Error: {e}'))


def format_file_name(downloads_path: str, journal_details_name: str) -> str:
    try:
        name_element_list = journal_details_name.replace('ı', 'i').replace('ğ', 'g').split()
        formatted_element_list = []
        for item in name_element_list:
            formatted_element_list.append(item.lower().strip() \
                                          .encode(encoding="ascii", errors="ignore").decode(encoding="UTF-8"))
        formatted_name = os.path.join(downloads_path, ("_".join(formatted_element_list) + ".pdf"))
        # remove linux reserved characters from formatted_name and cut it to 250 characters
        formatted_name = re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", formatted_name)
        formatted_name = formatted_name[:250]
        files = [os.path.join(downloads_path, file_name) for file_name in os.listdir(downloads_path)]

        os.rename(max(files, key=os.path.getctime), formatted_name)
        return formatted_name
    except Exception as e:
        send_notification(
            GeneralError(f'Error whilst formatting file name with dergipark_helper format_file_name. Error: {e}'))


def abstract_formatter(abstract, language) -> str:
    try:
        if language == "tr":
            abstract_head = abstract[:10]
            abstract_tail = abstract[10:]
            abstract_head = re.sub(r"\t|\n", "", abstract_head)
            abstract_head = re.sub(r"Öz:|Öz", "", abstract_head, flags=re.IGNORECASE)
            try:
                abstract_tail = abstract_tail[: abstract_tail.index("Anahtar ke")].strip()
            except:
                pass
            try:
                abstract_tail = abstract_tail[: abstract_tail.index("Anahtar Ke")].strip()
            except:
                pass
            try:
                abstract_tail = abstract_tail[: abstract_tail.index("anahtar ke:")].strip()
            except:
                pass
        else:
            abstract_head = abstract[:10]
            abstract_tail = abstract[10:]
            abstract_head = re.sub(r"\t|\n", "", abstract_head)
            abstract_head = re.sub(r"Summary:|ABSTRACT:", "", abstract_head, flags=re.IGNORECASE)
            abstract_head = re.sub(r"Summary|ABSTRACT", "", abstract_head, flags=re.IGNORECASE)
            try:
                abstract_tail = abstract_tail[: abstract_tail.index("keywords:")].strip()
            except:
                pass
            try:
                abstract_tail = abstract_tail[: abstract_tail.index("Keywords:")].strip()
            except:
                pass
            try:
                abstract_tail = abstract_tail[: abstract_tail.index("\nKeywords:")].strip()
            except:
                pass
        return (abstract_head + abstract_tail).strip()
    except Exception as e:
        send_notification(
            GeneralError(f'Error whilst formatting the abstract with dergipark_helper abstract_formatter. Error: {e}'))


if __name__ == "__main__":
    pass
