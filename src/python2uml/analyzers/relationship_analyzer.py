"""Relationship extraction from normalized AST."""

from __future__ import annotations

from python2uml.model.enums import ClassKind, RelationshipType
from python2uml.model.uml_diagram import UMLDiagram
from python2uml.model.uml_relationship import UMLRelationship
from python2uml.parsers.normalized_ast import NormalizedClass, NormalizedModule

RELATIONSHIP_RANK = {
    RelationshipType.ASSOCIATION: 1,
    RelationshipType.AGGREGATION: 2,
    RelationshipType.COMPOSITION: 3,
}


class RelationshipAnalyzer:
    def analyze(self, modules: list[NormalizedModule], diagram: UMLDiagram) -> UMLDiagram:
        for module in modules:
            for normalized_class in module.classes:
                self._add_class_relationships(normalized_class, diagram)
        return diagram

    def _add_class_relationships(self, normalized_class: NormalizedClass, diagram: UMLDiagram) -> None:
        if normalized_class.parent:
            self._add_relationship(diagram, normalized_class.parent, normalized_class.name, RelationshipType.COMPOSITION)

        for base_name in normalized_class.bases:
            if base_name not in diagram.classes:
                continue
            relationship_type = (
                RelationshipType.IMPLEMENTATION if diagram.classes[base_name].kind == ClassKind.INTERFACE and normalized_class.kind != ClassKind.INTERFACE else RelationshipType.INHERITANCE
            )
            self._add_relationship(diagram, normalized_class.name, base_name, relationship_type)

        for type_name in sorted(normalized_class.composed_types):
            self._add_relationship(diagram, normalized_class.name, type_name, RelationshipType.COMPOSITION)

        for assignment in normalized_class.member_assignments:
            relationship_type = RelationshipType.COMPOSITION if assignment.ownership in {"constructed", "value"} else RelationshipType.AGGREGATION
            self._add_relationship(diagram, normalized_class.name, assignment.type_name, relationship_type)

        for reference in normalized_class.type_references:
            self._add_relationship(diagram, normalized_class.name, reference.type_name, RelationshipType.ASSOCIATION)

        for method in normalized_class.methods:
            parameter_types = {parameter.name: parameter.type_name for parameter in method.parameters if parameter.type_name}
            for type_name in parameter_types.values():
                self._add_relationship(diagram, normalized_class.name, type_name, RelationshipType.ASSOCIATION)
            if method.return_type:
                self._add_relationship(diagram, normalized_class.name, method.return_type, RelationshipType.ASSOCIATION)
            for instantiation in method.local_instantiations:
                relationship_type = RelationshipType.COMPOSITION if method.is_constructor and instantiation.assigned_attribute else RelationshipType.ASSOCIATION
                self._add_relationship(diagram, normalized_class.name, instantiation.class_name, relationship_type)
            for insertion in method.append_calls:
                item_type = insertion.item_type or parameter_types.get(insertion.item_name)
                if item_type:
                    self._add_relationship(
                        diagram,
                        normalized_class.name,
                        item_type,
                        RelationshipType.AGGREGATION,
                    )

    def _add_relationship(self, diagram: UMLDiagram, source: str, target: str, relationship_type: RelationshipType) -> None:
        if source not in diagram.classes or target not in diagram.classes:
            return

        if relationship_type not in RELATIONSHIP_RANK:
            relationship = UMLRelationship(source, target, relationship_type)
            if relationship not in diagram.relationships:
                diagram.relationships.append(relationship)
            return

        existing = next(
            (relationship for relationship in diagram.relationships if relationship.source == source and relationship.target == target and relationship.relationship_type in RELATIONSHIP_RANK),
            None,
        )
        if existing is None:
            diagram.relationships.append(UMLRelationship(source, target, relationship_type))
        elif RELATIONSHIP_RANK[relationship_type] > RELATIONSHIP_RANK[existing.relationship_type]:
            diagram.relationships[diagram.relationships.index(existing)] = UMLRelationship(source, target, relationship_type)
