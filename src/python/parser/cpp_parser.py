"""C++ Tree-sitter adapter for the normalized AST boundary."""

from __future__ import annotations

from tree_sitter import Language, Node
import tree_sitter_cpp

from model.enums import ClassKind
from parser.normalized_ast import (
    NormalizedAttribute,
    NormalizedClass,
    NormalizedLocalInstantiation,
    NormalizedMemberAssignment,
    NormalizedMethod,
    NormalizedModule,
    NormalizedParameter,
    NormalizedTypeReference,
)
from parser.tree_sitter_helpers import node_text, parse_tree, tree_diagnostics, walk_named

CPP_LANGUAGE = Language(tree_sitter_cpp.language())
CLASS_NODES = {"class_specifier", "struct_specifier"}


class CppParser:
    def parse(self, *paths: str) -> list[NormalizedModule]:
        self._concrete_destructors: set[str] = set()
        self._method_qualifiers: dict[int, tuple[str, ...]] = {}
        parsed: list[tuple[bytes, Node, NormalizedModule]] = []
        for path in paths:
            source, root = parse_tree(path, CPP_LANGUAGE)
            classes: list[NormalizedClass] = []
            self._collect_classes(root, source, classes, None)
            parsed.append((source, root, NormalizedModule(path, classes, tree_diagnostics(path, root))))
        by_name = {item.name: item for _, _, module in parsed for item in module.classes}
        for source, root, _ in parsed:
            self._attach_definitions(root, source, by_name)
        declared = set(by_name)
        for item in by_name.values():
            for method in item.methods:
                method.local_instantiations[:] = [local for local in method.local_instantiations if local.class_name in declared]
            item.kind = self._class_kind(item, item.kind)
        return [module for _, _, module in parsed]

    def _collect_classes(self, node: Node, source: bytes, classes: list[NormalizedClass], parent: str | None) -> None:
        for child in node.named_children:
            if child.type in CLASS_NODES:
                normalized = self._normalize_class(child, source, parent)
                classes.append(normalized)
                body = child.child_by_field_name("body")
                if body is not None:
                    self._collect_classes(body, source, classes, normalized.name)
            else:
                self._collect_classes(child, source, classes, parent)

    def _normalize_class(self, node: Node, source: bytes, parent: str | None) -> NormalizedClass:
        name = node_text(source, node.child_by_field_name("name")) or ""
        default_visibility = "+" if node.type == "struct_specifier" else "-"
        visibility = default_visibility
        attributes: list[NormalizedAttribute] = []
        methods: list[NormalizedMethod] = []
        assignments: list[NormalizedMemberAssignment] = []
        references: list[NormalizedTypeReference] = []
        constructors: list[tuple[Node, NormalizedMethod]] = []
        body = node.child_by_field_name("body")
        if body is not None:
            for member in body.named_children:
                if member.type == "access_specifier":
                    visibility = self._visibility(node_text(source, member) or "")
                    continue
                declaration = self._method_declaration(member)
                if declaration is not None:
                    method = self._normalize_method(member, declaration, source, name, visibility)
                    methods.append(method)
                    references.extend(self._method_references(method))
                    if method.is_constructor:
                        constructors.append((member, method))
                elif member.type == "field_declaration" and not any(child.type in CLASS_NODES for child in member.named_children):
                    member_attributes, member_assignments = self._normalize_fields(member, source, visibility)
                    attributes.extend(member_attributes)
                    assignments.extend(member_assignments)
        for constructor, method in constructors:
            assignments.extend(self._initializer_assignments(constructor, method.parameters, attributes, source))
        return NormalizedClass(
            name=name,
            kind=ClassKind.STRUCT if node.type == "struct_specifier" else ClassKind.CLASS,
            parent=parent,
            bases=self._bases(node, source),
            attributes=attributes,
            methods=methods,
            member_assignments=assignments,
            type_references=references,
        )

    def _bases(self, node: Node, source: bytes) -> list[str]:
        clause = next((child for child in node.named_children if child.type == "base_class_clause"), None)
        if clause is None:
            return []
        return [self._relationship_name(node_text(source, child) or "") for child in clause.named_children if child.type != "access_specifier"]

    def _normalize_fields(self, node: Node, source: bytes, visibility: str) -> tuple[list[NormalizedAttribute], list[NormalizedMemberAssignment]]:
        type_node = node.child_by_field_name("type")
        attributes: list[NormalizedAttribute] = []
        assignments: list[NormalizedMemberAssignment] = []
        is_static = any(child.type == "storage_class_specifier" and node_text(source, child) == "static" for child in node.named_children)
        for declarator in self._field_declarators(node):
            name_node = self._identifier(declarator)
            if name_node is None:
                continue
            type_name = self._type_spelling(type_node, declarator, name_node, source)
            name = node_text(source, name_node) or ""
            attributes.append(NormalizedAttribute(name, type_name, visibility, is_static))
            if not is_static:
                ownership = "reference" if "*" in type_name or "&" in type_name else "value"
                assignments.append(NormalizedMemberAssignment(name, self._relationship_name(type_name), ownership))
        return attributes, assignments

    def _normalize_method(self, container: Node, declarator: Node, source: bytes, class_name: str, visibility: str) -> NormalizedMethod:
        name_node = declarator.child_by_field_name("declarator")
        name = self._declarator_name(name_node, source)
        parameters = self._parameters(declarator.child_by_field_name("parameters"), source)
        is_constructor = name == class_name
        pure = self._is_pure(container, source)
        if name.startswith("~") and container.child_by_field_name("body") is not None:
            self._concrete_destructors.add(class_name)
        method = NormalizedMethod(
            name=name,
            visibility=visibility,
            is_constructor=is_constructor,
            is_abstract=pure,
            is_pure_virtual=pure,
            is_static=any(child.type == "storage_class_specifier" and node_text(source, child) == "static" for child in container.named_children),
            parameters=parameters,
            return_type=None if is_constructor or name.startswith("~") else self._return_type(container, declarator, source),
        )
        body = container.child_by_field_name("body")
        if body is not None:
            method.local_instantiations.extend(self._local_instantiations(body, source))
        self._method_qualifiers[id(method)] = tuple(node_text(source, child) or "" for child in declarator.named_children if child.type in {"type_qualifier", "ref_qualifier"})
        return method

    def _attach_definitions(self, root: Node, source: bytes, classes: dict[str, NormalizedClass]) -> None:
        for node in walk_named(root):
            if node.type != "function_definition":
                continue
            declarator = self._method_declaration(node)
            if declarator is None:
                continue
            name_node = declarator.child_by_field_name("declarator")
            if name_node is None or name_node.type != "qualified_identifier":
                continue
            owner = self._relationship_name(node_text(source, name_node.child_by_field_name("scope")) or "")
            normalized_class = classes.get(owner)
            if normalized_class is None:
                continue
            method = self._normalize_method(node, declarator, source, owner, "+")
            signature = self._method_signature(method)
            existing = next((item for item in normalized_class.methods if self._method_signature(item) == signature), None)
            if existing is None:
                normalized_class.methods.append(method)
                existing = method
                normalized_class.type_references.extend(self._method_references(method))
            else:
                existing.parameters = method.parameters
                existing.return_type = method.return_type
                existing.local_instantiations = method.local_instantiations
                normalized_class.type_references.extend(NormalizedTypeReference(item.class_name, "local") for item in method.local_instantiations)
            if method.is_constructor:
                normalized_class.member_assignments.extend(self._initializer_assignments(node, method.parameters, normalized_class.attributes, source))

    def _initializer_assignments(self, node: Node, parameters: list[NormalizedParameter], attributes: list[NormalizedAttribute], source: bytes) -> list[NormalizedMemberAssignment]:
        parameter_types = {item.name: item.type_name for item in parameters}
        field_types = {item.name: item.type_name for item in attributes}
        result: list[NormalizedMemberAssignment] = []
        initializers = next((child for child in node.named_children if child.type == "field_initializer_list"), None)
        if initializers is None:
            return result
        for initializer in initializers.named_children:
            if initializer.type != "field_initializer" or len(initializer.named_children) < 2:
                continue
            member = node_text(source, initializer.named_children[0]) or ""
            arguments = initializer.named_children[1]
            value = arguments.named_children[0] if arguments.named_children else None
            value_name = node_text(source, value) if value is not None and value.type == "identifier" else None
            if value_name in parameter_types:
                result.append(NormalizedMemberAssignment(member, self._relationship_name(parameter_types[value_name] or ""), "supplied"))
            elif value is None:
                field_type = field_types.get(member) or ""
                if field_type and "*" not in field_type and "&" not in field_type:
                    result.append(NormalizedMemberAssignment(member, self._relationship_name(field_type), "constructed"))
            elif value.type == "new_expression":
                result.append(NormalizedMemberAssignment(member, self._relationship_name(node_text(source, value.child_by_field_name("type")) or ""), "constructed"))
            elif value.type == "compound_literal_expression":
                result.append(NormalizedMemberAssignment(member, self._relationship_name(node_text(source, value.child_by_field_name("type")) or ""), "constructed"))
        return result

    def _local_instantiations(self, body: Node, source: bytes) -> list[NormalizedLocalInstantiation]:
        result: list[NormalizedLocalInstantiation] = []
        for node in walk_named(body):
            if node.type != "declaration":
                continue
            type_name = self._relationship_name(node_text(source, node.child_by_field_name("type")) or "")
            for declarator in self._field_declarators(node):
                name_node = self._identifier(declarator)
                if name_node is not None:
                    result.append(NormalizedLocalInstantiation(type_name, assigned_name=node_text(source, name_node)))
        return result

    def _parameters(self, node: Node | None, source: bytes) -> list[NormalizedParameter]:
        if node is None:
            return []
        result: list[NormalizedParameter] = []
        for parameter in node.named_children:
            if parameter.type not in {"parameter_declaration", "optional_parameter_declaration"}:
                continue
            declarator = parameter.child_by_field_name("declarator")
            name_node = self._identifier(declarator) if declarator is not None else None
            name = node_text(source, name_node) or ""
            end = name_node.start_byte if name_node is not None else parameter.end_byte
            type_name = source[parameter.start_byte : end].decode("utf-8").strip()
            result.append(NormalizedParameter(name, type_name))
        return result

    def _method_references(self, method: NormalizedMethod) -> list[NormalizedTypeReference]:
        references = [NormalizedTypeReference(item.type_name, "parameter") for item in method.parameters if item.type_name]
        if method.return_type:
            references.append(NormalizedTypeReference(method.return_type, "return"))
        references.extend(NormalizedTypeReference(item.class_name, "local") for item in method.local_instantiations)
        return references

    def _method_declaration(self, node: Node) -> Node | None:
        declarator = node.child_by_field_name("declarator")
        while declarator is not None:
            if declarator.type == "function_declarator":
                return declarator
            declarator = declarator.child_by_field_name("declarator") or next(iter(declarator.named_children), None)
        return next((child for child in node.named_children if child.type == "function_declarator"), None)

    def _return_type(self, container: Node, declarator: Node, source: bytes) -> str | None:
        type_node = container.child_by_field_name("type")
        if type_node is None:
            return None
        outer = container.child_by_field_name("declarator") or declarator
        name_node = declarator.child_by_field_name("declarator")
        spelling = self._type_spelling(type_node, outer, name_node or declarator, source)
        qualifiers = [node_text(source, child) or "" for child in container.named_children if child.type == "type_qualifier" and child.end_byte <= type_node.start_byte]
        return " ".join([*qualifiers, spelling])

    def _method_signature(self, method: NormalizedMethod) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        return method.name, tuple((parameter.type_name or "").replace(" ", "") for parameter in method.parameters), self._method_qualifiers.get(id(method), ())

    def _field_declarators(self, node: Node) -> list[Node]:
        return [
            child
            for child in node.named_children
            if child == node.child_by_field_name("declarator") or child.type in {"field_identifier", "pointer_declarator", "reference_declarator", "init_declarator", "identifier"}
        ]

    def _identifier(self, node: Node | None) -> Node | None:
        if node is None:
            return None
        if node.type in {"identifier", "field_identifier"}:
            return node
        child = node.child_by_field_name("declarator")
        if child is not None:
            return self._identifier(child)
        return next((item for item in walk_named(node) if item.type in {"identifier", "field_identifier"}), None)

    def _declarator_name(self, node: Node | None, source: bytes) -> str:
        if node is None:
            return ""
        if node.type == "qualified_identifier":
            return self._declarator_name(node.child_by_field_name("name"), source)
        return node_text(source, node) or ""

    def _type_spelling(self, type_node: Node | None, declarator: Node, name_node: Node, source: bytes) -> str:
        base = node_text(source, type_node) or ""
        prefix = source[declarator.start_byte : name_node.start_byte].decode("utf-8").strip()
        return f"{base}{prefix}" if prefix in {"*", "&", "&&"} else f"{base} {prefix}".strip()

    def _is_pure(self, node: Node, source: bytes) -> bool:
        default = node.child_by_field_name("default_value")
        return (default is not None and node_text(source, default) == "0") or any(child.type == "pure_virtual_clause" for child in node.named_children)

    def _class_kind(self, normalized: NormalizedClass, original: ClassKind) -> ClassKind:
        pure_methods = [method for method in normalized.methods if method.is_pure_virtual]
        if not pure_methods:
            return original
        behavior = [method for method in normalized.methods if not method.is_constructor and not method.name.startswith("~")]
        has_instance_state = any(not attribute.is_static for attribute in normalized.attributes)
        if not has_instance_state and normalized.name not in self._concrete_destructors and behavior and all(method.visibility == "+" and method.is_pure_virtual for method in behavior):
            return ClassKind.INTERFACE
        return ClassKind.ABSTRACT_CLASS

    def _relationship_name(self, type_name: str) -> str:
        value = type_name.replace("const ", "").strip().rstrip("*& ")
        value = value.partition("<")[0].strip()
        return value.rsplit("::", 1)[-1]

    def _visibility(self, spelling: str) -> str:
        return "-" if spelling.startswith("private") else "#" if spelling.startswith("protected") else "+"
