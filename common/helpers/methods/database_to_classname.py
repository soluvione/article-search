"""A temporary helper module to convert Turkish names to ASCII"""


def journal_name_to_ascii(journal_name: str) -> str:
    journal_name = journal_name.strip()
    journal_name = journal_name.split()
    str_f = "_"
    objects_list = []

    for element in journal_name:
        objects_list.append(element.lower().encode(encoding="ascii", errors="ignore").decode(encoding="UTF-8"))

    return str_f.join(objects_list)
