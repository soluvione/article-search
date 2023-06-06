from enum import Enum


class ArticleType(Enum):
    OLGU = "OLGU SUNUMU"
    ORIJINAL = "ORİJİNAL ARAŞTIRMA"
    DERLEME = "DERLEME"
    GORUNTU = "ORİJİNAL GÖRÜNTÜ"
    EDITORDEN = "EDİTÖRDEN"
    MEKTUP = "EDİTÖRE MEKTUP"
    NOTLAR = "NOTLAR"

class AzureResponse(Enum):
    FAILURE = 0
    SUCCESSFUL = 1
    RUNNING = 2