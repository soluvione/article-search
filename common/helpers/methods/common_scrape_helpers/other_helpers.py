def check_article_type_pass(article_type: str):
    accepted_types = ["ORİJİNAL ARAŞTIRMA", "KLİNİK ARAŞTIRMA", "DERLEME", "OLGU SUNUMU", "ORİJİNAL GÖRÜNTÜ", "Editoryal"]
    if article_type in accepted_types:
        return True
    else:
        return False
