import pytest

from python2uml.analyzers.class_analyzer import ClassAnalyzer
from python2uml.analyzers.relationship_analyzer import RelationshipAnalyzer
from python2uml.model.enums import ClassKind, ProjectLanguage, RelationshipType
from python2uml.parsers.abstracter import AbstractSyntaxTreeLoader
from python2uml.parsers.python_parser import PythonParser


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


def test_dispatcher_defaults_to_python_for_compatibility(tmp_path):
    source = write_source(tmp_path, "legacy.py", "class Legacy:\n    pass\n")

    modules = AbstractSyntaxTreeLoader().load(str(source))

    assert modules[0].classes[0].name == "Legacy"


def test_non_constructor_member_construction_is_only_an_association(tmp_path):
    source = write_source(
        tmp_path,
        "refresh.py",
        "class Cache:\n    pass\n\nclass Service:\n    def refresh(self):\n        self.cache = Cache()\n",
    )
    modules = PythonParser().parse(str(source))
    service = class_by_name(modules[0], "Service")

    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)

    assert service.member_assignments == []
    assert [(relationship.source, relationship.target, relationship.relationship_type) for relationship in diagram.relationships] == [("Service", "Cache", RelationshipType.ASSOCIATION)]


def test_setter_preserves_supplied_member_assignment(tmp_path):
    source = write_source(
        tmp_path,
        "setter.py",
        'class Repo:\n    pass\n\nclass Service:\n    def set_repo(self, repo: "Repo"):\n        self.repo = repo\n',
    )

    service = class_by_name(PythonParser().parse(str(source))[0], "Service")

    assert assignment(service, "repo").ownership == "supplied"
    assert assignment(service, "repo").type_name == "Repo"


@pytest.mark.parametrize(
    "body",
    [
        "self.dependency = Dependency()\n        self.dependency = dependency",
        "self.dependency = dependency\n        self.dependency = Dependency()",
    ],
)
def test_constructor_preserves_competing_member_assignment_facts(tmp_path, body):
    source = write_source(
        tmp_path,
        "ownership.py",
        f'class Dependency:\n    pass\n\nclass Owner:\n    def __init__(self, dependency: "Dependency"):\n        {body}\n',
    )

    owner = class_by_name(PythonParser().parse(str(source))[0], "Owner")

    assert {item.ownership for item in owner.member_assignments if item.member_name == "dependency"} == {"constructed", "supplied"}


def test_abcmeta_keyword_marks_an_abstract_class(tmp_path):
    source = write_source(tmp_path, "abstract.py", "from abc import ABCMeta\n\nclass Model(metaclass=ABCMeta):\n    pass\n")

    model = class_by_name(PythonParser().parse(str(source))[0], "Model")

    assert model.kind is ClassKind.ABSTRACT_CLASS


def test_staticmethod_preserves_parameters_named_like_receivers(tmp_path):
    source = write_source(
        tmp_path,
        "static.py",
        'class Utility:\n    @staticmethod\n    def convert(self: "Input", cls: "Target") -> None:\n        pass\n',
    )

    method = class_by_name(PythonParser().parse(str(source))[0], "Utility").methods[0]

    assert [(parameter.name, parameter.type_name) for parameter in method.parameters] == [("self", "Input"), ("cls", "Target")]
