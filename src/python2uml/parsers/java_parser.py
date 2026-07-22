"""Java Tree-sitter adapter for the normalized AST boundary."""

from __future__ import annotations

from tree_sitter import Language, Node
import tree_sitter_java

from python2uml.model.enums import ClassKind
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
from python2uml.parsers.tree_sitter_helpers import node_text, parse_tree, tree_diagnostics

JAVA_LANGUAGE = Language(tree_sitter_java.language())
TYPE_DECLARATIONS = {"class_declaration", "interface_declaration", "enum_declaration"}


class JavaParser:
    def parse(self, *paths: str) -> list[NormalizedModule]:
        return [self._parse_path(path) for path in paths]

    def _parse_path(self, path: str) -> NormalizedModule:
        source, root = parse_tree(path, JAVA_LANGUAGE)
        classes: list[NormalizedClass] = []
        self._collect_classes(root, source, classes, None)
        return NormalizedModule(path, classes, tree_diagnostics(path, root))

    def _collect_classes(self, node: Node, source: bytes, classes: list[NormalizedClass], parent: str | None) -> None:
        for child in node.named_children:
            if child.type in TYPE_DECLARATIONS:
                normalized = self._normalize_class(child, source, parent)
                classes.append(normalized)
                body = child.child_by_field_name("body")
                if body is not None:
                    self._collect_classes(body, source, classes, normalized.name)
            else:
                self._collect_classes(child, source, classes, parent)

    def _normalize_class(self, node: Node, source: bytes, parent: str | None) -> NormalizedClass:
        name = node_text(source, node.child_by_field_name("name")) or ""
        modifiers = self._modifiers(node)
        kind = (
            ClassKind.INTERFACE
            if node.type == "interface_declaration"
            else ClassKind.ABSTRACT_CLASS if "abstract" in modifiers else ClassKind.ENUM if node.type == "enum_declaration" else ClassKind.CLASS
        )
        bases = self._bases(node, source)
        attributes: list[NormalizedAttribute] = []
        methods: list[NormalizedMethod] = []
        assignments: list[NormalizedMemberAssignment] = []
        references: list[NormalizedTypeReference] = []
        body = node.child_by_field_name("body")
        if body is not None:
            field_names = {
                node_text(source, declarator.child_by_field_name("name")) or ""
                for member in body.named_children
                if member.type == "field_declaration"
                for declarator in member.named_children
                if declarator.type == "variable_declarator"
            }
            for member in body.named_children:
                if member.type == "field_declaration":
                    member_attributes, member_assignments = self._normalize_fields(member, source)
                    attributes.extend(member_attributes)
                    assignments.extend(member_assignments)
                elif member.type in {"constructor_declaration", "method_declaration"}:
                    method, member_assignments = self._normalize_method(member, source, field_names)
                    methods.append(method)
                    assignments.extend(member_assignments)
                    references.extend(NormalizedTypeReference(parameter.type_name, "parameter") for parameter in method.parameters if parameter.type_name)
                    if method.return_type:
                        references.append(NormalizedTypeReference(method.return_type, "return"))
                    references.extend(NormalizedTypeReference(item.class_name, "local") for item in method.local_instantiations if not item.assigned_attribute)
        return NormalizedClass(name, kind, parent, bases, attributes, methods, member_assignments=assignments, type_references=references)

    def _bases(self, node: Node, source: bytes) -> list[str]:
        bases: list[str] = []
        superclass = node.child_by_field_name("superclass")
        if superclass is not None and superclass.named_children:
            bases.append(self._raw_type_name(superclass.named_children[0], source))
        interfaces = node.child_by_field_name("interfaces")
        if interfaces is not None:
            type_list = next((child for child in interfaces.named_children if child.type == "type_list"), interfaces)
            bases.extend(self._raw_type_name(child, source) for child in type_list.named_children)
        extends = next((child for child in node.named_children if child.type == "extends_interfaces"), None)
        if extends is not None:
            type_list = next((child for child in extends.named_children if child.type == "type_list"), extends)
            bases.extend(self._raw_type_name(child, source) for child in type_list.named_children)
        return bases

    def _normalize_fields(self, node: Node, source: bytes) -> tuple[list[NormalizedAttribute], list[NormalizedMemberAssignment]]:
        type_name = node_text(source, node.child_by_field_name("type"))
        modifiers = self._modifiers(node)
        attributes: list[NormalizedAttribute] = []
        assignments: list[NormalizedMemberAssignment] = []
        for declarator in (child for child in node.named_children if child.type == "variable_declarator"):
            name = node_text(source, declarator.child_by_field_name("name")) or ""
            attributes.append(NormalizedAttribute(name, type_name, self._visibility(modifiers), "static" in modifiers))
            value = declarator.child_by_field_name("value")
            if value is not None and value.type == "object_creation_expression":
                assignments.append(NormalizedMemberAssignment(name, self._raw_type_name(value.child_by_field_name("type"), source), "constructed"))
        return attributes, assignments

    def _normalize_method(self, node: Node, source: bytes, field_names: set[str]) -> tuple[NormalizedMethod, list[NormalizedMemberAssignment]]:
        is_constructor = node.type == "constructor_declaration"
        modifiers = self._modifiers(node)
        parameters = self._parameters(node.child_by_field_name("parameters"), source)
        parameter_types = {parameter.name: parameter.type_name for parameter in parameters if parameter.type_name}
        instantiations: list[NormalizedLocalInstantiation] = []
        insertions: list[NormalizedAppendCall] = []
        assignments: list[NormalizedMemberAssignment] = []
        body = node.child_by_field_name("body")
        if body is not None:
            shadowed_names = set(parameter_types)
            shadowed_names.update(
                node_text(source, declarator.child_by_field_name("name")) or ""
                for descendant in self._method_nodes(body)
                if descendant.type == "local_variable_declaration"
                for declarator in descendant.named_children
                if declarator.type == "variable_declarator"
            )
            for descendant in self._method_nodes(body):
                if descendant.type == "assignment_expression":
                    member = self._member_name(descendant.child_by_field_name("left"), source)
                    value = descendant.child_by_field_name("right")
                    if member and value is not None:
                        if value.type == "object_creation_expression":
                            type_name = self._raw_type_name(value.child_by_field_name("type"), source)
                            instantiations.append(NormalizedLocalInstantiation(type_name, assigned_attribute=member))
                            if is_constructor:
                                assignments.append(NormalizedMemberAssignment(member, type_name, "constructed"))
                        elif value.type == "identifier":
                            value_name = node_text(source, value) or ""
                            if value_name in parameter_types:
                                assignments.append(NormalizedMemberAssignment(member, self._relationship_name(parameter_types[value_name] or ""), "supplied"))
                elif descendant.type == "local_variable_declaration":
                    for declarator in (child for child in descendant.named_children if child.type == "variable_declarator"):
                        value = declarator.child_by_field_name("value")
                        if value is not None and value.type == "object_creation_expression":
                            instantiations.append(
                                NormalizedLocalInstantiation(
                                    self._raw_type_name(value.child_by_field_name("type"), source),
                                    assigned_name=node_text(source, declarator.child_by_field_name("name")),
                                )
                            )
                elif descendant.type == "method_invocation" and node_text(source, descendant.child_by_field_name("name")) == "add":
                    collection = self._collection_name(descendant.child_by_field_name("object"), source, field_names, shadowed_names)
                    arguments = descendant.child_by_field_name("arguments")
                    first_argument = arguments.named_children[0] if arguments is not None and arguments.named_children else None
                    if collection and first_argument is not None and first_argument.type == "identifier":
                        insertions.append(NormalizedAppendCall(collection, node_text(source, first_argument)))
        method = NormalizedMethod(
            name=node_text(source, node.child_by_field_name("name")) or "",
            visibility=self._visibility(modifiers),
            is_constructor=is_constructor,
            is_abstract="abstract" in modifiers or body is None,
            is_static="static" in modifiers,
            parameters=parameters,
            return_type=None if is_constructor else node_text(source, node.child_by_field_name("type")),
            local_instantiations=instantiations,
            append_calls=insertions,
        )
        return method, assignments

    def _parameters(self, node: Node | None, source: bytes) -> list[NormalizedParameter]:
        if node is None:
            return []
        return [
            NormalizedParameter(node_text(source, parameter.child_by_field_name("name")) or "", node_text(source, parameter.child_by_field_name("type")))
            for parameter in node.named_children
            if parameter.type in {"formal_parameter", "spread_parameter"}
        ]

    def _method_nodes(self, body: Node):
        stack = list(reversed(body.named_children))
        while stack:
            node = stack.pop()
            yield node
            if node.type not in TYPE_DECLARATIONS and node.type not in {"constructor_declaration", "method_declaration", "lambda_expression"}:
                stack.extend(reversed(node.named_children))

    def _member_name(self, node: Node | None, source: bytes) -> str | None:
        if node is None or node.type != "field_access":
            return None
        object_node = node.child_by_field_name("object")
        return node_text(source, node.child_by_field_name("field")) if object_node is not None and object_node.type == "this" else None

    def _collection_name(self, node: Node | None, source: bytes, field_names: set[str], shadowed_names: set[str]) -> str | None:
        if node is not None and node.type == "identifier":
            name = node_text(source, node)
            return name if name in field_names and name not in shadowed_names else None
        return self._member_name(node, source)

    def _raw_type_name(self, node: Node | None, source: bytes) -> str:
        if node is None:
            return ""
        if node.type == "generic_type" and node.named_children:
            return self._raw_type_name(node.named_children[0], source)
        if node.type == "scoped_type_identifier" and node.named_children:
            return self._raw_type_name(node.named_children[-1], source)
        return node_text(source, node) or ""

    def _relationship_name(self, type_name: str) -> str:
        return type_name.partition("<")[0].rsplit(".", 1)[-1]

    def _modifiers(self, node: Node) -> set[str]:
        modifiers = next((child for child in node.named_children if child.type == "modifiers"), None)
        return {child.type for child in modifiers.children} if modifiers is not None else set()

    def _visibility(self, modifiers: set[str]) -> str:
        return "-" if "private" in modifiers else "#" if "protected" in modifiers else "+"
