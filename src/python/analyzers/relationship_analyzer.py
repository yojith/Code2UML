"""Relationship extraction from AST."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from model.enums import RelationshipType
from model.uml_diagram import UMLDiagram
from model.uml_relationship import UMLRelationship
from utils.ast_utils import annotation_to_str


@dataclass(slots=True)
class ClassContext:
    name: str
    bases: set[str] = field(default_factory=set)
    self_attribute_types: dict[str, str] = field(default_factory=dict)
    local_instantiations: set[str] = field(default_factory=set)
    method_associations: set[str] = field(default_factory=set)
    parameter_types: dict[str, str] = field(default_factory=dict)
    parameter_names: set[str] = field(default_factory=set)
    append_targets: set[tuple[str, str]] = field(default_factory=set)


class RelationshipAnalyzer:
    def analyze(self, ast_trees: list[ast.AST], diagram: UMLDiagram) -> UMLDiagram:
        class_names = set(diagram.classes)
        for context in self._collect_contexts(ast_trees, class_names):
            self._add_inheritance(context, diagram)
            self._add_composition(context, class_names, diagram)
            self._add_aggregation(context, class_names, diagram)
            self._add_association(context, class_names, diagram)
        return diagram

    def _collect_contexts(self, ast_trees: list[ast.AST], class_names: set[str]) -> list[ClassContext]:
        contexts: list[ClassContext] = []
        for tree in ast_trees:
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name in class_names:
                    contexts.append(self._collect_context(node, class_names))
        return contexts

    def _collect_context(self, node: ast.ClassDef, class_names: set[str]) -> ClassContext:
        context = ClassContext(name=node.name)

        # Collect parent classes
        for base in node.bases:
            base_name = self._resolved_name(base)
            if base_name in class_names:
                context.bases.add(base_name)

        # Collect method parameter types and self attribute types
        for body_item in node.body:
            if not isinstance(body_item, ast.FunctionDef):
                continue
            parameter_types = self._function_parameter_types(body_item)
            context.parameter_types.update(parameter_types)
            context.parameter_names.update(name for name in parameter_types if name not in {"self", "cls"})

            # Collects assignments within methods
            for statement in body_item.body:
                self._collect_statement_facts(statement, context, class_names, body_item.name)
        return context

    def _collect_statement_facts(self, node: ast.AST, context: ClassContext, class_names: set[str], method_name: str) -> None:
        # Identify instantiation in __init__ and attribute type hints
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute) and self._is_self_attr(node.target):
            type_name = annotation_to_str(node.annotation)
            if type_name in class_names:
                context.self_attribute_types[node.target.attr] = type_name
            if method_name == "__init__" and isinstance(node.value, ast.Call):
                callee = self._resolved_name(node.value.func)
                if callee in class_names:
                    context.local_instantiations.add(callee)
        
        # Identify instantiation in __init__ without type hints
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and self._is_self_attr(target):
                    inferred = self._infer_call_type(node.value, class_names)
                    if inferred:
                        context.self_attribute_types.setdefault(target.attr, inferred)
                        if method_name == "__init__":
                            context.local_instantiations.add(inferred)
                elif isinstance(target, ast.Name) and isinstance(node.value, ast.Call) and method_name != "__init__":
                    callee = self._resolved_name(node.value.func)
                    if callee in class_names and target.id != "self":
                        context.method_associations.add(callee)
        elif isinstance(node, ast.Expr):
            call = node.value
            if isinstance(call, ast.Call):
                self._collect_call_heuristics(call, context, class_names)

        for child in ast.iter_child_nodes(node):
            self._collect_statement_facts(child, context, class_names, method_name)

    def _collect_call_heuristics(self, call: ast.Call, context: ClassContext, class_names: set[str]) -> None:
        if isinstance(call.func, ast.Attribute) and call.func.attr == "append" and isinstance(call.func.value, ast.Attribute):
            if self._is_self_attr(call.func.value) and call.args:
                argument_type = self._resolved_name(call.args[0]) if isinstance(call.args[0], ast.Name) else None
                if argument_type and argument_type in context.parameter_types:
                    context.append_targets.add((call.func.value.attr, context.parameter_types[argument_type]))

    def _add_inheritance(self, context: ClassContext, diagram: UMLDiagram) -> None:
        for base_name in context.bases:
            self._add_relationship(diagram, context.name, base_name, RelationshipType.INHERITANCE)

    def _add_composition(self, context: ClassContext, class_names: set[str], diagram: UMLDiagram) -> None:
        for type_name in context.local_instantiations:
            if type_name in class_names:
                self._add_relationship(diagram, context.name, type_name, RelationshipType.COMPOSITION)

    def _add_aggregation(self, context: ClassContext, class_names: set[str], diagram: UMLDiagram) -> None:
        for attr_type in context.self_attribute_types.values():
            if attr_type in class_names and not self._has_relationship(diagram, context.name, attr_type, RelationshipType.COMPOSITION):
                self._add_relationship(diagram, context.name, attr_type, RelationshipType.AGGREGATION)
        for _, target_type in context.append_targets:
            if target_type in class_names and not self._has_relationship(diagram, context.name, target_type, RelationshipType.COMPOSITION):
                self._add_relationship(diagram, context.name, target_type, RelationshipType.AGGREGATION)

    def _add_association(self, context: ClassContext, class_names: set[str], diagram: UMLDiagram) -> None:
        for target in context.method_associations:
            if target in class_names and not self._has_relationship(diagram, context.name, target, RelationshipType.COMPOSITION):
                self._add_relationship(diagram, context.name, target, RelationshipType.ASSOCIATION)
        for parameter_type in context.parameter_types.values():
            if parameter_type in class_names and not self._has_relationship(diagram, context.name, parameter_type, RelationshipType.COMPOSITION):
                self._add_relationship(diagram, context.name, parameter_type, RelationshipType.ASSOCIATION)

    def _add_relationship(self, diagram: UMLDiagram, source: str, target: str, relationship_type: RelationshipType) -> None:
        existing = next((rel for rel in diagram.relationships if rel.source == source and rel.target == target), None)
        if existing is None:
            diagram.relationships.append(UMLRelationship(source, target, relationship_type))
            return
        if self._relationship_rank(relationship_type) < self._relationship_rank(existing.relationship_type):
            diagram.relationships.remove(existing)
            diagram.relationships.append(UMLRelationship(source, target, relationship_type))

    def _has_relationship(self, diagram: UMLDiagram, source: str, target: str, relationship_type: RelationshipType) -> bool:
        return any(rel.source == source and rel.target == target and rel.relationship_type == relationship_type for rel in diagram.relationships)

    def _relationship_rank(self, relationship_type: RelationshipType) -> int:
        return {
            RelationshipType.INHERITANCE: 0,
            RelationshipType.COMPOSITION: 1,
            RelationshipType.AGGREGATION: 2,
            RelationshipType.ASSOCIATION: 3,
        }[relationship_type]

    def _function_parameter_types(self, node: ast.FunctionDef) -> dict[str, str]:
        result: dict[str, str] = {}
        for arg in node.args.args:
            type_name = annotation_to_str(arg.annotation)
            if type_name:
                result[arg.arg] = type_name
        return result

    def _infer_call_type(self, value: ast.AST, class_names: set[str]) -> str | None:
        if isinstance(value, ast.Call):
            callee = self._resolved_name(value.func)
            if callee in class_names:
                return callee
        return None

    def _resolved_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_self_attr(self, node: ast.Attribute) -> bool:
        return isinstance(node.value, ast.Name) and node.value.id == "self"
