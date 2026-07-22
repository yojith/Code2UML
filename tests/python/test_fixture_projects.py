from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from python2uml.analyzers.class_analyzer import ClassAnalyzer
from python2uml.analyzers.relationship_analyzer import RelationshipAnalyzer
from python2uml.model.enums import ProjectLanguage
from python2uml.parsers.abstracter import AbstractSyntaxTreeLoader
from python2uml.parsers.project_loader import ProjectLoader

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


def expected_class(name, kind="class", parent=None, attributes=(), methods=()):
    return (name, kind, parent, tuple(sorted(attributes)), tuple(sorted(methods)))


PYTHON_PROJECT2_CLASSES = [
    expected_class("Address", attributes=(("city", "str", "+"),), methods=(("__init__", ("city: str",), None, "+"),)),
    expected_class("AuditLog", attributes=(("entries", "list[str]", "+"),), methods=(("__init__", (), None, "+"), ("record", ("message: str",), "None", "+"))),
    expected_class("Entity", "abstract_class", attributes=(("entity_id", "str", "+"),), methods=(("__init__", ("entity_id: str",), None, "+"), ("key", (), "str", "+"))),
    expected_class("Profile", attributes=(("bio", "str", "+"),), methods=(("__init__", ("bio: str",), None, "+"),)),
    expected_class(
        "Project",
        attributes=(("owner", "User", "+"), ("tasks", "list[Task]", "+"), ("team", "Team", "+")),
        methods=(
            ("__init__", ("entity_id: str", "owner: User", "team: Team"), None, "+"),
            ("add_task", ("task: Task",), "None", "+"),
            ("archive", ("repository: Repository",), "None", "+"),
            ("key", (), "str", "+"),
        ),
    ),
    expected_class("Repository", "interface", methods=(("find", ("key: str",), "Entity", "+"), ("save", ("entity: Entity",), "None", "+"))),
    expected_class("Settings", parent="User", attributes=(("notifications", "bool", "+"),), methods=(("__init__", ("notifications: bool",), None, "+"),)),
    expected_class(
        "Task",
        attributes=(("assignee", "User", "+"), ("audit", "AuditLog", "+")),
        methods=(("__init__", ("entity_id: str", "assignee: User"), None, "+"), ("key", (), "str", "+"), ("reassign", ("user: User",), "None", "+")),
    ),
    expected_class(
        "Team",
        attributes=(("audit", "AuditLog", "+"), ("members", "list[User]", "+"), ("repository", "Repository", "+")),
        methods=(("__init__", ("repository: Repository",), None, "+"), ("add", ("user: User",), "None", "+"), ("primary_profile", ("user: User",), "Profile", "+")),
    ),
    expected_class(
        "User",
        attributes=(("address", "Address", "+"), ("audit", "AuditLog", "+"), ("profile", "Profile", "+"), ("settings", "Settings", "+")),
        methods=(("__init__", ("entity_id: str", "address: Address"), None, "+"), ("find", ("key: str",), "Entity", "+"), ("key", (), "str", "+"), ("save", ("entity: Entity",), "None", "+")),
    ),
]

JVM_PROJECT2_CLASSES = [
    expected_class("Address", attributes=(("city", "String", "+"),), methods=(("Address", ("city: String",), None, "+"),)),
    expected_class("AuditLog", attributes=(("entries", "List<String>", "-"),), methods=(("record", ("message: String",), "void", "+"),)),
    expected_class("Entity", "abstract_class", attributes=(("id", "String", "#"),), methods=(("Entity", ("id: String",), None, "+"), ("key", (), "String", "+"))),
    expected_class("Profile", attributes=(("bio", "String", "+"),), methods=(("Profile", ("bio: String",), None, "+"),)),
    expected_class(
        "Project",
        attributes=(("owner", "User", "-"), ("tasks", "List<Task>", "-"), ("team", "Team", "-")),
        methods=(
            ("Project", ("id: String", "owner: User", "team: Team"), None, "+"),
            ("addTask", ("task: Task",), "void", "+"),
            ("archive", ("repository: Repository",), "void", "+"),
            ("key", (), "String", "+"),
        ),
    ),
    expected_class("Repository", "interface", methods=(("find", ("key: String",), "Entity", "+"), ("save", ("entity: Entity",), "void", "+"))),
    expected_class("Settings", parent="User", attributes=(("notifications", "boolean", "+"),), methods=(("Settings", ("notifications: boolean",), None, "+"),)),
    expected_class(
        "Task",
        attributes=(("assignee", "User", "-"), ("audit", "AuditLog", "-")),
        methods=(("Task", ("id: String", "assignee: User"), None, "+"), ("key", (), "String", "+"), ("reassign", ("user: User",), "void", "+")),
    ),
    expected_class(
        "Team",
        attributes=(("audit", "AuditLog", "-"), ("members", "List<User>", "-"), ("repository", "Repository", "-")),
        methods=(("Team", ("repository: Repository",), None, "+"), ("add", ("user: User",), "void", "+"), ("primaryProfile", ("user: User",), "Profile", "+")),
    ),
    expected_class(
        "User",
        attributes=(("address", "Address", "-"), ("audit", "AuditLog", "-"), ("profile", "Profile", "-"), ("settings", "Settings", "-")),
        methods=(("User", ("id: String", "address: Address"), None, "+"), ("find", ("key: String",), "Entity", "+"), ("key", (), "String", "+"), ("save", ("entity: Entity",), "void", "+")),
    ),
]

CPP_PROJECT2_CLASSES = [
    expected_class("Address", "struct", attributes=(("city", "std::string", "+"),)),
    expected_class("AuditLog", "struct", attributes=(("entries", "int", "+"),), methods=(("record", ("message: const std::string&",), "void", "+"),)),
    expected_class("Entity", "abstract_class", attributes=(("id", "std::string", "#"),), methods=(("key", (), "std::string", "+"),)),
    expected_class("Profile", "struct", attributes=(("bio", "std::string", "+"),)),
    expected_class(
        "Project",
        attributes=(("owner", "User*", "-"), ("tasks", "std::vector<Task*>", "-"), ("team", "Team*", "-")),
        methods=(
            ("Project", ("owner: User*", "team: Team*"), None, "+"),
            ("add_task", ("task: Task*",), "void", "+"),
            ("archive", ("repository: Repository*",), "void", "+"),
            ("key", (), "std::string", "+"),
        ),
    ),
    expected_class("Repository", "interface", methods=(("find", ("key: const std::string&",), "Entity*", "+"), ("save", ("entity: Entity*",), "void", "+"))),
    expected_class("Settings", "struct", "User", (("notifications", "bool", "+"),)),
    expected_class(
        "Task",
        attributes=(("assignee", "User*", "-"), ("audit", "AuditLog", "-")),
        methods=(("Task", ("assignee: User*",), None, "+"), ("key", (), "std::string", "+"), ("reassign", ("user: User*",), "void", "+")),
    ),
    expected_class(
        "Team",
        attributes=(("audit", "AuditLog", "-"), ("members", "std::vector<User*>", "-"), ("repository", "Repository*", "-")),
        methods=(("Team", ("repository: Repository*",), None, "+"), ("add", ("user: User*",), "void", "+"), ("primary_profile", ("user: User*",), "Profile*", "+")),
    ),
    expected_class(
        "User",
        attributes=(("address", "Address*", "-"), ("audit", "AuditLog", "-"), ("profile", "Profile", "-"), ("settings", "Settings", "-")),
        methods=(("User", ("address: Address*",), None, "+"), ("find", ("key: const std::string&",), "Entity*", "+"), ("key", (), "std::string", "+"), ("save", ("entity: Entity*",), "void", "+")),
    ),
]

C_PROJECT2_CLASSES = [
    expected_class("Address", "struct", "domain_h", (("city", "char*", "+"),)),
    expected_class("AuditLog", "struct", "work_h", (("entries", "int", "+"),), (("audit_record", ("message: char*",), "void", "+"),)),
    expected_class("Entity", "struct", "domain_h", (("id", "int", "+"),)),
    expected_class("Profile", "struct", "domain_h", (("bio", "char*", "+"),)),
    expected_class(
        "Project",
        "struct",
        "work_h",
        (("base", "struct Entity", "+"), ("owner", "struct User*", "+"), ("tasks", "struct Task*", "+"), ("team", "struct Team*", "+")),
        (("project_add_task", ("task: struct Task*",), "void", "+"), ("project_archive", ("repository: struct Entity*",), "void", "+")),
    ),
    expected_class(
        "Task", "struct", "work_h", (("assignee", "struct User*", "+"), ("audit", "struct AuditLog", "+"), ("base", "struct Entity", "+")), (("task_reassign", ("user: struct User*",), "void", "+"),)
    ),
    expected_class("Team", "struct", "work_h", (("audit", "struct AuditLog", "+"), ("members", "struct User*", "+")), (("team_add", ("user: struct User*",), "void", "+"),)),
    expected_class(
        "User",
        "struct",
        "domain_h",
        (("address", "struct Address*", "+"), ("base", "struct Entity", "+"), ("notifications", "int", "+"), ("profile", "struct Profile", "+")),
        (("user_key", (), "int", "+"), ("user_move", ("address: struct Address*",), "void", "+"), ("user_profile", (), "struct Profile*", "+")),
    ),
    expected_class("domain_c"),
    expected_class("domain_h", attributes=(("PROFILE_LIMIT", "macro", "+"),)),
    expected_class("work_c"),
    expected_class("work_h", attributes=(("PROJECT_TASK_LIMIT", "macro", "+"), ("TEAM_LIMIT", "macro", "+"))),
]


CASES = [
    (
        "python",
        "project1",
        {
            "classes": [
                expected_class("Cart", attributes=(("items", "list[Product]", "+"),), methods=(("__init__", (), None, "+"), ("add", ("product: Product",), "None", "+"))),
                expected_class("Product", attributes=(("sku", None, "+"),), methods=(("__init__", ("sku: str",), None, "+"),)),
            ],
            "relationships": [("Cart", "Product", "aggregation")],
            "diagnostics": [],
        },
    ),
    (
        "python",
        "project2",
        {
            "classes": PYTHON_PROJECT2_CLASSES,
            "relationships": [
                ("Project", "Entity", "inheritance"),
                ("Project", "Repository", "association"),
                ("Project", "Task", "aggregation"),
                ("Project", "Team", "aggregation"),
                ("Project", "User", "aggregation"),
                ("Repository", "Entity", "association"),
                ("Task", "AuditLog", "composition"),
                ("Task", "Entity", "inheritance"),
                ("Task", "User", "aggregation"),
                ("Team", "AuditLog", "composition"),
                ("Team", "Profile", "association"),
                ("Team", "Repository", "aggregation"),
                ("Team", "User", "aggregation"),
                ("User", "Address", "aggregation"),
                ("User", "AuditLog", "composition"),
                ("User", "Entity", "association"),
                ("User", "Entity", "inheritance"),
                ("User", "Profile", "composition"),
                ("User", "Repository", "implementation"),
                ("User", "Settings", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "java",
        "project1",
        {
            "classes": [
                expected_class("Cart", attributes=(("featured", "Product", "-"),), methods=(("Cart", ("featured: Product",), None, "+"), ("add", ("product: Product",), "void", "+"))),
                expected_class("Product", attributes=(("sku", "String", "+"),)),
            ],
            "relationships": [("Cart", "Product", "aggregation")],
            "diagnostics": [],
        },
    ),
    (
        "java",
        "project2",
        {
            "classes": JVM_PROJECT2_CLASSES,
            "relationships": [
                ("Project", "Entity", "inheritance"),
                ("Project", "Repository", "association"),
                ("Project", "Task", "aggregation"),
                ("Project", "Team", "aggregation"),
                ("Project", "User", "aggregation"),
                ("Repository", "Entity", "association"),
                ("Task", "AuditLog", "composition"),
                ("Task", "Entity", "inheritance"),
                ("Task", "User", "aggregation"),
                ("Team", "AuditLog", "composition"),
                ("Team", "Profile", "association"),
                ("Team", "Repository", "aggregation"),
                ("Team", "User", "aggregation"),
                ("User", "Address", "aggregation"),
                ("User", "AuditLog", "composition"),
                ("User", "Entity", "association"),
                ("User", "Entity", "inheritance"),
                ("User", "Profile", "composition"),
                ("User", "Repository", "implementation"),
                ("User", "Settings", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "cpp",
        "project1",
        {
            "classes": [
                expected_class("Cart", attributes=(("featured", "Product*", "-"),), methods=(("add", ("product: Product*",), "void", "+"),)),
                expected_class("Product", "struct", attributes=(("sku", "int", "+"),)),
            ],
            "relationships": [("Cart", "Product", "aggregation")],
            "diagnostics": [],
        },
    ),
    (
        "cpp",
        "project2",
        {
            "classes": CPP_PROJECT2_CLASSES,
            "relationships": [
                ("Project", "Entity", "inheritance"),
                ("Project", "Repository", "association"),
                ("Project", "Task", "aggregation"),
                ("Project", "Team", "aggregation"),
                ("Project", "User", "aggregation"),
                ("Repository", "Entity", "association"),
                ("Task", "AuditLog", "composition"),
                ("Task", "Entity", "inheritance"),
                ("Task", "User", "aggregation"),
                ("Team", "AuditLog", "composition"),
                ("Team", "Profile", "association"),
                ("Team", "Repository", "aggregation"),
                ("Team", "User", "aggregation"),
                ("User", "Address", "aggregation"),
                ("User", "AuditLog", "composition"),
                ("User", "Entity", "association"),
                ("User", "Entity", "inheritance"),
                ("User", "Profile", "composition"),
                ("User", "Repository", "implementation"),
                ("User", "Settings", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "c",
        "project1",
        {
            "classes": [
                expected_class("Cart", "struct", "shop_h", (("featured", "struct Product*", "+"),), (("cart_add", ("product: struct Product*",), "void", "+"),)),
                expected_class("Product", "struct", "shop_h", (("sku", "int", "+"),)),
                expected_class("shop_c"),
                expected_class("shop_h", attributes=(("CART_LIMIT", "macro", "+"),)),
            ],
            "relationships": [
                ("Cart", "Product", "aggregation"),
                ("shop_c", "shop_h", "association"),
                ("shop_h", "Cart", "composition"),
                ("shop_h", "Product", "composition"),
            ],
            "diagnostics": [],
        },
    ),
    (
        "c",
        "project2",
        {
            "classes": C_PROJECT2_CLASSES,
            "relationships": [
                ("Project", "Entity", "composition"),
                ("Project", "Task", "aggregation"),
                ("Project", "Team", "aggregation"),
                ("Project", "User", "aggregation"),
                ("Task", "AuditLog", "composition"),
                ("Task", "Entity", "composition"),
                ("Task", "User", "aggregation"),
                ("Team", "AuditLog", "composition"),
                ("Team", "User", "aggregation"),
                ("User", "Address", "aggregation"),
                ("User", "Entity", "composition"),
                ("User", "Profile", "composition"),
                ("domain_c", "domain_h", "association"),
                ("domain_h", "Address", "composition"),
                ("domain_h", "Entity", "composition"),
                ("domain_h", "Profile", "composition"),
                ("domain_h", "User", "composition"),
                ("work_c", "work_h", "association"),
                ("work_h", "AuditLog", "composition"),
                ("work_h", "Project", "composition"),
                ("work_h", "Task", "composition"),
                ("work_h", "Team", "composition"),
                ("work_h", "domain_h", "association"),
            ],
            "diagnostics": [],
        },
    ),
]


def summarize_classes(modules, diagram):
    parents = {normalized_class.name: normalized_class.parent for module in modules for normalized_class in module.classes}
    return sorted(
        (
            name,
            uml_class.kind.value,
            parents[name],
            tuple(sorted((attribute.name, attribute.type_name, attribute.visibility) for attribute in uml_class.attributes)),
            tuple(sorted((method.name, tuple(method.parameters), method.return_type, method.visibility) for method in uml_class.methods)),
        )
        for name, uml_class in diagram.classes.items()
    )


def summarize_relationships(diagram):
    return sorted((item.source, item.target, item.relationship_type.value) for item in diagram.relationships)


def summarize_diagnostics(modules):
    return sorted((item.path, item.line, item.column, item.severity, item.message) for module in modules for item in module.diagnostics)


@pytest.mark.parametrize("language,project,expected", CASES)
def test_fixture_project(language, project, expected):
    project_language = ProjectLanguage(language)
    root = FIXTURES / language / project
    files = ProjectLoader().collect_source_files(project_language, str(root))
    modules = AbstractSyntaxTreeLoader().load(project_language, *files)
    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)

    assert summarize_classes(modules, diagram) == expected["classes"]
    assert summarize_relationships(diagram) == expected["relationships"]
    assert summarize_diagnostics(modules) == expected["diagnostics"]


def test_module_cli_accepts_language_and_prints_diagnostics(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "python2uml",
            "--project-type",
            "java",
            "--paths",
            str(FIXTURES / "java" / "project2"),
            "--output",
            str(tmp_path / "fixture.drawio"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["classes"]
    assert payload["relationships"]
    assert payload["diagnostics"] == []
