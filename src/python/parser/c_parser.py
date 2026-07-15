"""C Tree-sitter adapter and UML file-class mapping."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from tree_sitter import Language, Node
import tree_sitter_c

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

C_LANGUAGE = Language(tree_sitter_c.language())


class CParser:
    def parse(self, *paths: str) -> list[NormalizedModule]:
        names = self._file_class_names(paths)
        parsed: list[tuple[bytes, Node, NormalizedModule, NormalizedClass]] = []
        structs: dict[str, NormalizedClass] = {}
        for path in paths:
            source, root = parse_tree(path, C_LANGUAGE)
            file_class = NormalizedClass(names[str(Path(path).resolve())])
            classes = [file_class]
            self._collect_structs(root, source, file_class.name, classes, structs)
            module = NormalizedModule(path, classes, tree_diagnostics(path, root))
            parsed.append((source, root, module, file_class))

        declared = set(structs)
        path_to_file = {str(Path(module.path).resolve()): file_class for _, _, module, file_class in parsed}
        basename_to_files: dict[str, list[NormalizedClass]] = defaultdict(list)
        for path, file_class in path_to_file.items():
            basename_to_files[Path(path).name].append(file_class)

        attached: dict[tuple[str, str, tuple[str | None, ...]], NormalizedMethod] = {}
        for source, root, module, file_class in parsed:
            self._populate_file(root, source, module.path, file_class, structs, declared, path_to_file, basename_to_files, attached)

        for item in structs.values():
            item.member_assignments[:] = [assignment for assignment in item.member_assignments if assignment.type_name in declared]
        return [module for _, _, module, _ in parsed]

    def _collect_structs(
        self,
        root: Node,
        source: bytes,
        file_name: str,
        classes: list[NormalizedClass],
        structs: dict[str, NormalizedClass],
    ) -> None:
        seen: set[int] = set()
        for node in walk_named(root):
            if node.type != "struct_specifier" or node.child_by_field_name("body") is None or node.id in seen:
                continue
            seen.add(node.id)
            name = node_text(source, node.child_by_field_name("name")) or self._anonymous_struct_name(node, source)
            if not name or name in structs:
                continue
            attributes, assignments = self._fields(node.child_by_field_name("body"), source)
            normalized = NormalizedClass(name, ClassKind.STRUCT, file_name, attributes=attributes, member_assignments=assignments)
            classes.append(normalized)
            structs[name] = normalized

    def _anonymous_struct_name(self, node: Node, source: bytes) -> str:
        container = node.parent
        if container is None:
            return ""
        declarator = container.child_by_field_name("declarator")
        identifier = self._identifier(declarator)
        return node_text(source, identifier) or ""

    def _fields(self, body: Node | None, source: bytes) -> tuple[list[NormalizedAttribute], list[NormalizedMemberAssignment]]:
        attributes: list[NormalizedAttribute] = []
        assignments: list[NormalizedMemberAssignment] = []
        if body is None:
            return attributes, assignments
        for field in body.named_children:
            if field.type != "field_declaration":
                continue
            type_node = field.child_by_field_name("type")
            for declarator in self._declarators(field):
                identifier = self._identifier(declarator)
                if identifier is None:
                    continue
                name = node_text(source, identifier) or ""
                type_name = self._type_spelling(type_node, declarator, identifier, source)
                attributes.append(NormalizedAttribute(name, type_name))
                assignments.append(NormalizedMemberAssignment(name, self._type_endpoint(type_name), "reference" if self._has_pointer(declarator) else "value"))
        return attributes, assignments

    def _populate_file(
        self,
        root: Node,
        source: bytes,
        path: str,
        file_class: NormalizedClass,
        structs: dict[str, NormalizedClass],
        declared: set[str],
        path_to_file: dict[str, NormalizedClass],
        basename_to_files: dict[str, list[NormalizedClass]],
        attached: dict[tuple[str, str, tuple[str | None, ...]], NormalizedMethod],
    ) -> None:
        for node in root.named_children:
            if node.type in {"preproc_def", "preproc_function_def"}:
                name = node_text(source, node.child_by_field_name("name")) or ""
                if name:
                    file_class.attributes.append(NormalizedAttribute(name, "macro", is_static=True))
            elif node.type == "preproc_include":
                target = self._include_target(node, source, path, path_to_file, basename_to_files)
                if target is not None:
                    file_class.type_references.append(NormalizedTypeReference(target.name, "include"))
            elif node.type in {"declaration", "function_definition"}:
                function = self._function_declarator(node)
                if function is not None:
                    self._attach_function(node, function, source, file_class, structs, declared, attached)
                elif node.type == "declaration" and not any(child.type == "struct_specifier" and child.child_by_field_name("body") is not None for child in node.named_children):
                    file_class.attributes.extend(self._global_attributes(node, source))

    def _include_target(
        self,
        node: Node,
        source: bytes,
        source_path: str,
        path_to_file: dict[str, NormalizedClass],
        basename_to_files: dict[str, list[NormalizedClass]],
    ) -> NormalizedClass | None:
        path_node = node.child_by_field_name("path")
        spelling = (node_text(source, path_node) or "").strip('"<>')
        resolved = str((Path(source_path).parent / spelling).resolve())
        if resolved in path_to_file:
            return path_to_file[resolved]
        matches = basename_to_files.get(Path(spelling).name, [])
        return matches[0] if len(matches) == 1 else None

    def _attach_function(
        self,
        container: Node,
        declarator: Node,
        source: bytes,
        file_class: NormalizedClass,
        structs: dict[str, NormalizedClass],
        declared: set[str],
        attached: dict[tuple[str, str, tuple[str | None, ...]], NormalizedMethod],
    ) -> None:
        name = node_text(source, self._identifier(declarator.child_by_field_name("declarator"))) or ""
        parameters = self._parameters(declarator.child_by_field_name("parameters"), source)
        parameter_nodes = [child for child in (declarator.child_by_field_name("parameters") or declarator).named_children if child.type == "parameter_declaration"]
        owner = None
        if parameters and parameter_nodes and self._has_pointer(parameter_nodes[0].child_by_field_name("declarator")):
            owner = structs.get(self._type_endpoint(parameters[0].type_name or ""))
        method_parameters = parameters[1:] if owner is not None else parameters
        method = NormalizedMethod(
            name,
            parameters=method_parameters,
            return_type=self._return_type(container, source),
            local_instantiations=self._locals(container.child_by_field_name("body"), source, declared),
        )
        target = owner or file_class
        references = [NormalizedTypeReference(self._type_endpoint(parameter.type_name or ""), "parameter") for parameter in method_parameters]
        if method.return_type:
            references.append(NormalizedTypeReference(self._type_endpoint(method.return_type), "return"))
        for reference in references:
            if reference.type_name in declared and reference not in target.type_references:
                target.type_references.append(reference)
        key = (target.name, name, tuple(parameter.type_name for parameter in method_parameters))
        existing = attached.get(key)
        if existing is None:
            target.methods.append(method)
            attached[key] = method
        elif method.local_instantiations:
            existing.local_instantiations = method.local_instantiations

    def _parameters(self, node: Node | None, source: bytes) -> list[NormalizedParameter]:
        if node is None:
            return []
        result: list[NormalizedParameter] = []
        for parameter in node.named_children:
            if parameter.type != "parameter_declaration":
                continue
            type_node = parameter.child_by_field_name("type")
            declarator = parameter.child_by_field_name("declarator")
            identifier = self._identifier(declarator)
            name = node_text(source, identifier) or ""
            type_name = self._type_spelling(type_node, declarator, identifier, source) if declarator is not None and identifier is not None else node_text(source, type_node)
            if type_name == "void" and not name:
                continue
            result.append(NormalizedParameter(name, type_name))
        return result

    def _locals(self, body: Node | None, source: bytes, declared: set[str]) -> list[NormalizedLocalInstantiation]:
        if body is None:
            return []
        result: list[NormalizedLocalInstantiation] = []
        for node in walk_named(body):
            if node.type != "declaration" or self._function_declarator(node) is not None:
                continue
            type_name = self._type_endpoint(node_text(source, node.child_by_field_name("type")) or "")
            if type_name not in declared:
                continue
            for declarator in self._declarators(node):
                identifier = self._identifier(declarator)
                if identifier is not None:
                    result.append(NormalizedLocalInstantiation(type_name, node_text(source, identifier)))
        return result

    def _global_attributes(self, declaration: Node, source: bytes) -> list[NormalizedAttribute]:
        type_node = declaration.child_by_field_name("type")
        result: list[NormalizedAttribute] = []
        for declarator in self._declarators(declaration):
            identifier = self._identifier(declarator)
            if identifier is None:
                continue
            result.append(NormalizedAttribute(node_text(source, identifier) or "", self._type_spelling(type_node, declarator, identifier, source), is_static=True))
        return result

    def _return_type(self, node: Node, source: bytes) -> str | None:
        type_name = node_text(source, node.child_by_field_name("type"))
        declarator = node.child_by_field_name("declarator")
        while declarator is not None and declarator.type != "function_declarator":
            if declarator.type == "pointer_declarator":
                type_name = f"{type_name}*"
            declarator = declarator.child_by_field_name("declarator")
        return type_name

    def _function_declarator(self, node: Node) -> Node | None:
        declarator = node.child_by_field_name("declarator")
        while declarator is not None:
            if declarator.type == "function_declarator":
                return declarator
            declarator = declarator.child_by_field_name("declarator")
        return None

    def _declarators(self, node: Node) -> list[Node]:
        return [
            child
            for child in node.named_children
            if child == node.child_by_field_name("declarator") or child.type in {"identifier", "field_identifier", "pointer_declarator", "array_declarator", "init_declarator"}
        ]

    def _identifier(self, node: Node | None) -> Node | None:
        if node is None:
            return None
        if node.type in {"identifier", "field_identifier", "type_identifier"}:
            return node
        child = node.child_by_field_name("declarator")
        if child is not None:
            return self._identifier(child)
        return next((item for item in walk_named(node) if item.type in {"identifier", "field_identifier", "type_identifier"}), None)

    def _has_pointer(self, node: Node | None) -> bool:
        return node is not None and any(item.type == "pointer_declarator" for item in walk_named(node))

    def _type_spelling(self, type_node: Node | None, declarator: Node, identifier: Node, source: bytes) -> str:
        base = node_text(source, type_node) or ""
        if type_node is not None and type_node.type == "struct_specifier" and type_node.child_by_field_name("body") is not None:
            base = f"struct {node_text(source, type_node.child_by_field_name('name')) or node_text(source, identifier) or ''}".strip()
        prefix = source[declarator.start_byte : identifier.start_byte].decode("utf-8").strip()
        return f"{base}{prefix}" if prefix == "*" else base

    def _type_endpoint(self, spelling: str) -> str:
        value = spelling.replace("*", " ").strip()
        parts = [part for part in value.split() if part not in {"const", "volatile", "struct"}]
        return parts[-1] if parts else ""

    def _file_class_names(self, paths: tuple[str, ...]) -> dict[str, str]:
        resolved = [Path(path).resolve() for path in paths]
        result = {str(path): self._safe_name(path.name) for path in resolved}
        groups: dict[str, list[Path]] = defaultdict(list)
        for path in resolved:
            groups[result[str(path)]].append(path)
        for base, group in groups.items():
            if len(group) < 2:
                continue
            depth = 1
            while True:
                candidates = {str(path): self._safe_name("_".join(path.parts[-(depth + 1) :])) for path in group}
                if len(set(candidates.values())) == len(group):
                    result.update(candidates)
                    break
                depth += 1
                if depth >= max(len(path.parts) for path in group):
                    for index, path in enumerate(sorted(group, key=lambda item: str(item).casefold()), 1):
                        result[str(path)] = f"{base}_{index}"
                    break
        return result

    def _safe_name(self, value: str) -> str:
        return "".join(character if character.isalnum() else "_" for character in value).strip("_")
