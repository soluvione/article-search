import re
from difflib import SequenceMatcher


def similarity(a, b):
    """
    Calculate the similarity between two strings using SequenceMatcher.

    :param a: The first string.
    :param b: The second string.
    :return: The similarity ratio between the two strings.
    """
    return SequenceMatcher(None, a, b).ratio()


def remove_duplicates(arr):
    """
    Remove duplicate elements from the given array while preserving the original order.

    :param arr: The input array.
    :return: A new array containing only unique elements from the input array.
    """
    return list(dict.fromkeys(arr))


def associate_authors_data(author_names, author_emails, author_specialities):
    """
    Associate author names with their corresponding email addresses and speciality/university information.

    :param author_names: An array of author names.
    :param author_emails: An array of author email addresses.
    :param author_specialities: An array of author speciality/university data.
    :return: An array of dictionaries containing the associated author data.
    """
    # Remove duplicate author names and emails
    author_names = remove_duplicates(author_names)
    author_emails = remove_duplicates(author_emails)

    author_data = []

    single_email = None
    if len(author_emails) == 1 and not re.match(r"^[a-z]\s", author_emails[0]):
        single_email = author_emails[0]

    for name in author_names:
        author_info = {"name": re.sub(r"[\*\d,]+[a-z]*", "", name).strip(),
                       "speciality": None,
                       "email": None}

        # Extract the suffix information
        suffix = re.search(r"[\d\*]+[a-z]*$", name)
        if suffix:
            suffix = suffix.group(0)

        # Extract the speciality/university information
        if suffix:
            for speciality in author_specialities:
                if speciality.startswith(suffix):
                    author_info["speciality"] = speciality[len(suffix):].strip()
                    break

        # Assign speciality for authors without suffix
        if author_info["speciality"] is None:
            for speciality in author_specialities:
                if re.match(r"^(\d+|[a-z]+|\*)\s", speciality) is None:
                    author_info["speciality"] = speciality.strip()
                    break

        # Extract the email information
        if suffix:
            for email in author_emails:
                if email.startswith(suffix):
                    author_info["email"] = email[len(suffix):].strip()
                    break
        elif single_email:
            author_info["email"] = single_email if similarity(author_info["name"].lower(), single_email.split('@')[0].lower()) > 0.6 else None

        author_data.append(author_info)

    return author_data
