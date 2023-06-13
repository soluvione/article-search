import re
from fuzzywuzzy import fuzz
import random
from operator import itemgetter

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
    author_data = []

    # Single author and single email case
    if len(author_names) == 1 and len(author_emails) == 1:
        author_info = {"name": re.sub(r"[\*\d,]+[a-z]*$", "", author_names[0]).strip(), "email": author_emails[0], "speciality": None}

        # Directly pair speciality if only one exists
        if len(author_specialities) == 1:
            author_info["speciality"] = author_specialities[0]

        author_data.append(author_info)
        return author_data

    # Calculate the similarity scores for all combinations of authors and emails
    similarities = []
    for name in author_names:
        for email in author_emails:
            email_prefix = email.split('@')[0]
            similarity_score = fuzz.ratio(name.lower(), email_prefix.lower())
            similarities.append((name, email, similarity_score))

    # Sort the similarities by score in descending order
    similarities.sort(key=itemgetter(2), reverse=True)

    # Assign emails to authors based on the highest similarity scores
    assigned_emails = set()
    for name, email, _ in similarities:
        if email not in assigned_emails:
            assigned_emails.add(email)

            author_info = {"name": re.sub(r"[\*\d,]+[a-z]*$", "", name).strip(),
                           "email": email,
                           "speciality": None}

            # Extract the suffix information
            suffixes = re.findall(r"[\d\*,]+[a-z]*$", name)
            for suffix in suffixes:
                # Check if the suffix is used for emails
                email_match = False
                for author_email in author_emails:
                    if author_email.startswith(suffix):
                        email_match = True
                        author_info["email"] = author_email
                        author_emails.remove(author_email)
                        break

                # If the suffix is not used for emails, check for specialities
                if not email_match:
                    for speciality in author_specialities:
                        if speciality.startswith(suffix):
                            author_info["speciality"] = speciality[len(suffix):].strip()
                            break

            # If no speciality is assigned yet, assign the first available one
            if author_info["speciality"] is None and author_specialities:
                author_info["speciality"] = author_specialities[0]
                author_specialities.remove(author_specialities[0])

            author_data.append(author_info)

    return author_data


# OLD VERSION
"""
def associate_authors_data(author_names, author_emails, author_specialities):
    ""
    Associate author names with their corresponding email addresses and speciality/university information.

    :param author_names: An array of author names.
    :param author_emails: An array of author email addresses.
    :param author_specialities: An array of author speciality/university data.
    :return: An array of dictionaries containing the associated author data.
    ""
    # Remove duplicate author names and emails
    author_names = remove_duplicates(author_names)
    author_emails = remove_duplicates(author_emails)

    author_data = []

    # Calculate the similarity scores for all combinations of authors and emails
    similarities = []
    for name in author_names:
        for email in author_emails:
            email_prefix = email.split('@')[0]
            similarity_score = fuzz.ratio(name.lower(), email_prefix.lower())
            similarities.append((name, email, similarity_score))

    # Sort the similarities by score in descending order
    similarities.sort(key=itemgetter(2), reverse=True)

    # Assign emails to authors based on the highest similarity scores
    assigned_emails = set()
    for name, email, _ in similarities:
        if email not in assigned_emails:
            assigned_emails.add(email)

            author_info = {"name": re.sub(r"[\*\d,]+[a-z]*", "", name).strip(),
                           "email": email,
                           "speciality": None}

            # Extract the suffix information
            suffix = re.search(r"[\d\*]+[a-z]*$", name)
            if suffix:
                suffix = suffix.group(0)

            # Extract the speciality/university information
            if suffix:
                for speciality in author_specialities:
                    if suffix in speciality:  # Change from `startswith` to `in`
                        author_info["speciality"] = speciality.strip()
                        break

            # Assign speciality for authors without suffix
            if author_info["speciality"] is None:
                # Choose a random speciality for the author
                if len(author_specialities) > 0:
                    random_speciality = random.choice(author_specialities)
                    author_info["speciality"] = random_speciality.strip()

            author_data.append(author_info)

    return author_data
"""

# OLDEST VERSION
"""
import re
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz

def similarity(a, b):
    ""
    Calculate the similarity between two strings using SequenceMatcher.

    :param a: The first string.
    :param b: The second string.
    :return: The similarity ratio between the two strings.
    ""
    return SequenceMatcher(None, a, b).ratio()


def remove_duplicates(arr):
    ""
    Remove duplicate elements from the given array while preserving the original order.

    :param arr: The input array.
    :return: A new array containing only unique elements from the input array.
    ""
    return list(dict.fromkeys(arr))


def associate_authors_data(author_names, author_emails, author_specialities):
    ""
    Associate author names with their corresponding email addresses and speciality/university information.

    :param author_names: An array of author names.
    :param author_emails: An array of author email addresses.
    :param author_specialities: An array of author speciality/university data.
    :return: An array of dictionaries containing the associated author data.
    ""
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
        best_match_score = 0
        best_match_email = None
        for email in author_emails:
            # Split the email on the "@" symbol and get the first part
            email_prefix = email.split('@')[0]

            # Calculate the similarity score between the email prefix and the author name
            similarity_score = fuzz.ratio(author_info["name"].lower(), email_prefix.lower())

            # If this score is the highest we've seen so far, save the email
            if similarity_score > best_match_score:
                best_match_score = similarity_score
                best_match_email = email

        # Assign the best match email to the author info
        if best_match_score > 40:  # Adjust this threshold as needed
            author_info["email"] = best_match_email
            author_emails.remove(best_match_email)

        author_data.append(author_info)

    return author_data
"""