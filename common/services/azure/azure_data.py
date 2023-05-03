from typing import Any, List, TypeVar, Type, cast, Callable


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_float(x: Any) -> float:
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def to_float(x: Any) -> float:
    assert isinstance(x, float)
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


class AuthorMail:
    type: str
    value_string: str
    content: str
    confidence: float

    def __init__(self, type: str, value_string: str, content: str, confidence: float) -> None:
        self.type = type
        self.value_string = value_string
        self.content = content
        self.confidence = confidence

    @staticmethod
    def from_dict(obj: Any) -> 'AuthorMail':
        assert isinstance(obj, dict)
        type = from_str(obj.get("type"))
        value_string = from_str(obj.get("valueString"))
        content = from_str(obj.get("content"))
        confidence = from_float(obj.get("confidence"))
        return AuthorMail(type, value_string, content, confidence)

    def to_dict(self) -> dict:
        result: dict = {}
        result["type"] = from_str(self.type)
        result["valueString"] = from_str(self.value_string)
        result["content"] = from_str(self.content)
        result["confidence"] = to_float(self.confidence)
        return result


class Fields:
    author_mail: AuthorMail

    def __init__(self, author_mail: AuthorMail) -> None:
        self.author_mail = author_mail

    @staticmethod
    def from_dict(obj: Any) -> 'Fields':
        assert isinstance(obj, dict)
        author_mail = AuthorMail.from_dict(obj.get("author_mail"))
        return Fields(author_mail)

    def to_dict(self) -> dict:
        result: dict = {}
        result["author_mail"] = to_class(AuthorMail, self.author_mail)
        return result


class Document:
    doc_type: str
    fields: Fields

    def __init__(self, doc_type: str, fields: Fields) -> None:
        self.doc_type = doc_type
        self.fields = fields

    @staticmethod
    def from_dict(obj: Any) -> 'Document':
        assert isinstance(obj, dict)
        doc_type = from_str(obj.get("docType"))
        fields = Fields.from_dict(obj.get("fields"))
        return Document(doc_type, fields)

    def to_dict(self) -> dict:
        result: dict = {}
        result["docType"] = from_str(self.doc_type)
        result["fields"] = to_class(Fields, self.fields)
        return result


class AnalyzeResult:
    content: str
    documents: List[Document]

    def __init__(self, content: str, documents: List[Document]) -> None:
        self.content = content
        self.documents = documents

    @staticmethod
    def from_dict(obj: Any) -> 'AnalyzeResult':
        assert isinstance(obj, dict)
        content = from_str(obj.get("content"))
        documents = from_list(Document.from_dict, obj.get("documents"))
        return AnalyzeResult(content, documents)

    def to_dict(self) -> dict:
        result: dict = {}
        result["content"] = from_str(self.content)
        result["documents"] = from_list(lambda x: to_class(Document, x), self.documents)
        return result


class AzureData:
    status: str
    analyze_result: AnalyzeResult

    def __init__(self, status: str, analyze_result: AnalyzeResult) -> None:
        self.status = status
        self.analyze_result = analyze_result

    @staticmethod
    def from_dict(obj: Any) -> 'AzureData':
        assert isinstance(obj, dict)
        status = from_str(obj.get("status"))
        analyze_result = AnalyzeResult.from_dict(obj.get("analyzeResult"))
        return AzureData(status, analyze_result)

    def to_dict(self) -> dict:
        result: dict = {}
        result["status"] = from_str(self.status)
        result["analyzeResult"] = to_class(AnalyzeResult, self.analyze_result)
        return result


def azure_data_from_dict(s: Any) -> AzureData:
    return AzureData.from_dict(s)


def azure_data_to_dict(x: AzureData) -> Any:
    return to_class(AzureData, x)
