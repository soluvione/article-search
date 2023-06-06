import re
from collections import defaultdict


class Author:
    def __init__(self, name):
        self.name = name


def name_similarity(name_parts, email_parts):
    score = 0
    for part in name_parts:
        if part in email_parts:
            score += 1
    return score / max(len(name_parts), len(email_parts))


def pair_authors_and_emails(author_objects, emails):
    author_names = [author.name for author in author_objects]
    author_parts = [re.findall(r'\w+', author_name.lower()) for author_name in author_names]
    email_parts = [re.findall(r'\w+', email.split('@')[0].lower()) for email in emails]
    author_scores = defaultdict(dict)

    for author_idx, author in enumerate(author_parts):
        for email_idx, email in enumerate(email_parts):
            author_scores[author_idx][email_idx] = name_similarity(author, email)

    paired_authors = {}
    paired_emails = set()
    unmatched_emails = []

    for _ in range(min(len(author_objects), len(emails))):
        max_score = -1
        max_author_idx, max_email_idx = None, None

        for author_idx in range(len(author_objects)):
            if author_idx in paired_authors:
                continue

            for email_idx in range(len(emails)):
                if email_idx in paired_emails:
                    continue

                score = author_scores[author_idx][email_idx]
                if score > max_score:
                    max_score = score
                    max_author_idx, max_email_idx = author_idx, email_idx

        if max_score > 0:
            paired_authors[max_author_idx] = emails[max_email_idx]
            paired_emails.add(max_email_idx)
        else:
            break

    for email_idx in range(len(emails)):
        if email_idx not in paired_emails:
            unmatched_emails.append(emails[email_idx])

    return {author_objects[k].name: v for k, v in paired_authors.items()}, unmatched_emails


author_objects = [Author(name='Alice Smith'), Author(name='Bob Johnson'), Author(name='Charlie Brown'), Author(name='David Thompson')]
emails = ['asmith@example.com', 'b.johnson@example.com', 'cbrown@example.com', 'd.thompson@example.com',
          'unmatched@example.com']

paired, unmatched = pair_authors_and_emails(author_objects, emails)
print('Paired:', paired)
print('Unmatched:', unmatched)
