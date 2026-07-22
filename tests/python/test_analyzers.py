import pytest

from python2uml.analyzers.class_analyzer import ClassAnalyzer
from python2uml.analyzers.relationship_analyzer import RelationshipAnalyzer
from python2uml.model.enums import ClassKind, RelationshipType
from python2uml.parsers.normalized_ast import (
    NormalizedAppendCall,
    NormalizedAttribute,
    NormalizedClass,
    NormalizedLocalInstantiation,
    NormalizedMemberAssignment,
    NormalizedMethod,
    NormalizedModule,
    NormalizedParameter,
    NormalizedTypeReference,
)


def relationships(diagram, source, target):
    return {relationship.relationship_type for relationship in diagram.relationships if relationship.source == source and relationship.target == target}


def module_with_classes(source, target, evidence=()):
    owner = NormalizedClass(name=source)
    for relationship_type in evidence:
        if relationship_type == "association":
            owner.type_references.append(NormalizedTypeReference(target, "local"))
        elif relationship_type == "aggregation":
            owner.member_assignments.append(NormalizedMemberAssignment("target", target, "supplied"))
        elif relationship_type == "composition":
            owner.member_assignments.append(NormalizedMemberAssignment("target", target, "constructed"))
    return NormalizedModule(path="example.py", classes=[owner, NormalizedClass(name=target)])


def module_with_external_base_and_parameter(class_name, base_name, parameter_type):
    return NormalizedModule(
        path="controller.py",
        classes=[
            NormalizedClass(
                name=class_name,
                bases=[base_name],
                methods=[NormalizedMethod("handle", parameters=[NormalizedParameter("request", parameter_type)])],
                type_references=[NormalizedTypeReference(parameter_type, "parameter")],
            )
        ],
    )


def test_class_analyzer_preserves_normalized_class_kinds_and_members():
    modules = [
        NormalizedModule(
            path="types.py",
            classes=[
                NormalizedClass(
                    name="Service",
                    kind=ClassKind.ABSTRACT_CLASS,
                    attributes=[NormalizedAttribute("endpoint", "str", "-")],
                    methods=[NormalizedMethod("run", parameters=[NormalizedParameter("count", "int")], return_type="None")],
                ),
                NormalizedClass(name="Port", kind=ClassKind.INTERFACE),
            ],
        )
    ]

    diagram = ClassAnalyzer().analyze(modules)

    assert diagram.classes["Service"].kind == ClassKind.ABSTRACT_CLASS
    assert diagram.classes["Service"].attributes[0].type_name == "str"
    assert diagram.classes["Service"].methods[0].parameters == ["count: int"]
    assert diagram.classes["Port"].kind == ClassKind.INTERFACE


def test_nested_class_is_composed_by_parent():
    modules = [NormalizedModule(path="nested.py", classes=[NormalizedClass("Outer"), NormalizedClass("Inner", parent="Outer")])]
    diagram = ClassAnalyzer().analyze(modules)

    RelationshipAnalyzer().analyze(modules, diagram)

    assert relationships(diagram, "Outer", "Inner") == {RelationshipType.COMPOSITION}


def test_concrete_class_implements_project_interface():
    modules = [
        NormalizedModule(
            path="service.java",
            classes=[
                NormalizedClass("Port", kind=ClassKind.INTERFACE),
                NormalizedClass("Service", bases=["Port"]),
            ],
        )
    ]
    diagram = ClassAnalyzer().analyze(modules)

    RelationshipAnalyzer().analyze(modules, diagram)

    assert relationships(diagram, "Service", "Port") == {RelationshipType.IMPLEMENTATION}


def test_strongest_relationship_evidence_wins():
    modules = [module_with_classes("Order", "Customer", evidence=("composition", "aggregation", "association"))]
    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    assert relationships(diagram, "Order", "Customer") == {RelationshipType.COMPOSITION}


def test_external_types_stay_in_signatures_without_edges():
    modules = [module_with_external_base_and_parameter("Controller", "FrameworkBase", "Request")]
    diagram = ClassAnalyzer().analyze(modules)
    RelationshipAnalyzer().analyze(modules, diagram)
    assert set(diagram.classes) == {"Controller"}
    assert diagram.relationships == []
    assert "request: Request" in diagram.classes["Controller"].methods[0].parameters


@pytest.mark.parametrize(
    "candidate",
    [
        NormalizedClass("Controller", member_assignments=[NormalizedMemberAssignment("request", "External", "constructed")]),
        NormalizedClass("Controller", methods=[NormalizedMethod("handle", return_type="External")]),
        NormalizedClass(
            "Controller",
            methods=[NormalizedMethod("handle", local_instantiations=[NormalizedLocalInstantiation("External", assigned_name="request")])],
        ),
        NormalizedClass("Controller", type_references=[NormalizedTypeReference("External", "local")]),
    ],
    ids=["member-assignment", "return", "instantiation", "type-reference"],
)
def test_external_relationship_candidates_are_suppressed(candidate):
    modules = [NormalizedModule(path="controller.py", classes=[candidate])]
    diagram = ClassAnalyzer().analyze(modules)

    RelationshipAnalyzer().analyze(modules, diagram)

    assert diagram.relationships == []


def test_collection_insertion_uses_canonical_item_type():
    modules = [
        NormalizedModule(
            path="team.hpp",
            classes=[
                NormalizedClass(
                    "Team",
                    methods=[
                        NormalizedMethod(
                            "add",
                            parameters=[NormalizedParameter("user", "User*")],
                            append_calls=[NormalizedAppendCall("members", "user", "User")],
                        )
                    ],
                ),
                NormalizedClass("User"),
            ],
        )
    ]
    diagram = ClassAnalyzer().analyze(modules)

    RelationshipAnalyzer().analyze(modules, diagram)

    assert relationships(diagram, "Team", "User") == {RelationshipType.AGGREGATION}
