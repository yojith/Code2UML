from model.enums import ClassKind, ProjectLanguage
from parser.abstracter import AbstractSyntaxTreeLoader
from parser.python_parser import PythonParser


def class_by_name(module, name):
    return next(normalized_class for normalized_class in module.classes if normalized_class.name == name)


def assignment(normalized_class, member_name):
    return next(item for item in normalized_class.member_assignments if item.member_name == member_name)


def write_source(tmp_path, name, source):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_python_parser_normalizes_abstraction_and_ownership(tmp_path):
    source = write_source(
        tmp_path,
        "service.py",
        """
from abc import ABC, abstractmethod
from typing import Protocol

class Repository(Protocol):
    async def get(self, key: "Key") -> "Record": ...

class BaseService(ABC):
    @abstractmethod
    def run(self) -> None: ...

class Cache:
    pass

class Service:
    class State:
        pass

    def __init__(self, repository: "Repository"):
        self.repository = repository
        self.cache: Cache = Cache()
        self.records: list[Record] = []

    async def store(self, record: "Record") -> "Record":
        self.records.append(record)
        temporary = Cache()
        return record
""",
    )

    module = PythonParser().parse(str(source))[0]

    repository = class_by_name(module, "Repository")
    base_service = class_by_name(module, "BaseService")
    service = class_by_name(module, "Service")
    assert repository.kind is ClassKind.INTERFACE
    assert repository.methods[0].parameters[0].type_name == "Key"
    assert repository.methods[0].return_type == "Record"
    assert base_service.kind is ClassKind.ABSTRACT_CLASS
    assert base_service.methods[0].is_abstract
    assert class_by_name(module, "State").parent == "Service"
    assert assignment(service, "repository").ownership == "supplied"
    assert assignment(service, "repository").type_name == "Repository"
    assert assignment(service, "cache").ownership == "constructed"
    assert assignment(service, "cache").type_name == "Cache"
    store = next(method for method in service.methods if method.name == "store")
    assert store.parameters[0].type_name == "Record"
    assert store.return_type == "Record"
    assert store.append_calls[0].collection_attribute == "records"
    assert store.append_calls[0].item_name == "record"
    assert store.local_instantiations[0].class_name == "Cache"


def test_python_parser_returns_valid_classes_and_diagnostic_for_malformed_source(tmp_path):
    source = write_source(
        tmp_path,
        "broken.py",
        "class Before:\n    pass\n\ndef broken(:\n    pass\n\nclass After:\n    pass\n",
    )

    module = PythonParser().parse(str(source))[0]

    assert [normalized_class.name for normalized_class in module.classes] == ["Before", "After"]
    assert len(module.diagnostics) == 1
    diagnostic = module.diagnostics[0]
    assert diagnostic.path == str(source)
    assert diagnostic.line == 4
    assert diagnostic.column > 0
    assert diagnostic.severity == "error"
    assert diagnostic.message


def test_dispatcher_registers_the_python_adapter(tmp_path):
    source = write_source(tmp_path, "model.py", "class Model:\n    pass\n")

    modules = AbstractSyntaxTreeLoader().load(ProjectLanguage.PYTHON, str(source))

    assert modules[0].classes[0].name == "Model"
