"""Python ``ast`` adapter for the normalized AST boundary."""

from __future__ import annotations

import ast
from pathlib import Path

from model.enums import ClassKind
from parser.normalized_ast import (
    NormalizedAppendCall,
    NormalizedAttribute,
    NormalizedClass,
    NormalizedLocalInstantiation,
    NormalizedMemberAssignment,
    NormalizedMethod,
    NormalizedModule,
    NormalizedParameter,
    NormalizedTypeReference,
    SourceDiagnostic,
)
from utils.ast_utils import annotation_to_str, is_private
from utils.type_resolver import normalize_type_name


class PythonParser:
    def parse(self, *paths: str) -> list[NormalizedModule]:
        return [self._parse_path(path) for path in paths]

    def _parse_path(self, path: str) -> NormalizedModule:
        source = Path(path).read_text(encoding="utf-8")
        diagnostics: list[SourceDiagnostic] = []
        try:
            nodes = ast.parse(source, filename=path).body
        except SyntaxError as error:
            diagnostics.append(
                SourceDiagnostic(
                    path=path,
                    line=error.lineno or 1,
                    column=error.offset or 1,
                    severity="error",
                    message=error.msg,
                )
            )
            nodes = self._recover_statements(source, path)

        classes = [normalized for node in nodes if isinstance(node, ast.ClassDef) for normalized in self._normalize_classes(node)]
        return NormalizedModule(path=path, classes=classes, diagnostics=diagnostics)

    def _recover_statements(self, source: str, path: str) -> list[ast.stmt]:
        if not source.strip():
            return []
        try:
            return ast.parse(source, filename=path).body
        except SyntaxError as error:
            lines = source.splitlines(keepends=True)
            start = min(max((error.lineno or 1) - 1, 0), len(lines) - 1)
            end = min(max(error.end_lineno or error.lineno or 1, start + 1), len(lines))
            before = "".join(lines[:start])
            after = "".join(lines[end:])
            if before == source or after == source:
                return []
            return [*self._recover_statements(before, path), *self._recover_statements(after, path)]

    def _normalize_classes(self, node: ast.ClassDef, parent: str | None = None) -> list[NormalizedClass]:
        normalized = self._normalize_class(node, parent)
        nested = [child for item in node.body if isinstance(item, ast.ClassDef) for child in self._normalize_classes(item, node.name)]
        return [normalized, *nested]

    def _normalize_class(self, node: ast.ClassDef, parent: str | None) -> NormalizedClass:
        attributes: list[NormalizedAttribute] = []
        methods: list[NormalizedMethod] = []
        assignments: list[NormalizedMemberAssignment] = []
        references: list[NormalizedTypeReference] = []
        seen_attributes: set[str] = set()

        for item in node.body:
            candidates: list[NormalizedAttribute] = []
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method = self._normalize_method(item)
                methods.append(method)
                candidates = self._attributes_from_method(item)
                assignments.extend(self._member_assignments(item, method.parameters, include_constructed=method.is_constructor))
                references.extend(self._method_references(method))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                candidates = [self._attribute(item.target.id, annotation_to_str(item.annotation), is_static=True)]

            for attribute in candidates:
                if attribute.name not in seen_attributes:
                    seen_attributes.add(attribute.name)
                    attributes.append(attribute)

        bases = [name for base in node.bases if (name := self._resolved_name(base))]
        has_abstract_method = any(method.is_abstract for method in methods)
        has_abstract_metaclass = any(keyword.arg == "metaclass" and self._resolved_name(keyword.value) == "ABCMeta" for keyword in node.keywords)
        kind = ClassKind.INTERFACE if "Protocol" in bases else ClassKind.ABSTRACT_CLASS if {"ABC", "ABCMeta"} & set(bases) or has_abstract_method or has_abstract_metaclass else ClassKind.CLASS
        return NormalizedClass(
            name=node.name,
            kind=kind,
            parent=parent,
            bases=bases,
            attributes=attributes,
            methods=methods,
            member_assignments=assignments,
            type_references=references,
        )

    def _normalize_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> NormalizedMethod:
        decorators = {self._resolved_name(decorator) for decorator in node.decorator_list}
        positional = [*node.args.posonlyargs, *node.args.args]
        if "staticmethod" not in decorators and positional:
            positional = positional[1:]
        parameters = [NormalizedParameter(arg.arg, normalize_type_name(annotation_to_str(arg.annotation))) for arg in [*positional, *node.args.kwonlyargs]]
        if node.args.vararg:
            parameters.append(NormalizedParameter(node.args.vararg.arg, normalize_type_name(annotation_to_str(node.args.vararg.annotation))))
        if node.args.kwarg:
            parameters.append(NormalizedParameter(node.args.kwarg.arg, normalize_type_name(annotation_to_str(node.args.kwarg.annotation))))

        instantiations: list[NormalizedLocalInstantiation] = []
        append_calls: list[NormalizedAppendCall] = []
        for inner in self._iter_method_nodes(node.body):
            if isinstance(inner, (ast.Assign, ast.AnnAssign)):
                value = inner.value
                class_name = self._call_target_name(value)
                targets = inner.targets if isinstance(inner, ast.Assign) else [inner.target]
                if class_name:
                    for target in targets:
                        if isinstance(target, ast.Attribute) and self._is_self_attribute(target):
                            instantiations.append(NormalizedLocalInstantiation(class_name, assigned_attribute=target.attr))
                        elif isinstance(target, ast.Name):
                            instantiations.append(NormalizedLocalInstantiation(class_name, assigned_name=target.id))
            elif isinstance(inner, ast.Call) and (append_call := self._append_call(inner)):
                append_calls.append(append_call)

        return NormalizedMethod(
            name=node.name,
            visibility="-" if is_private(node.name) and node.name != "__init__" else "+",
            is_constructor=node.name == "__init__",
            is_abstract="abstractmethod" in decorators,
            is_static="staticmethod" in decorators,
            parameters=parameters,
            return_type=normalize_type_name(annotation_to_str(node.returns)),
            local_instantiations=instantiations,
            append_calls=append_calls,
        )

    def _attributes_from_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[NormalizedAttribute]:
        attributes: list[NormalizedAttribute] = []
        for inner in self._iter_method_nodes(node.body):
            if isinstance(inner, ast.AnnAssign) and isinstance(inner.target, ast.Attribute) and self._is_self_attribute(inner.target):
                attributes.append(self._attribute(inner.target.attr, annotation_to_str(inner.annotation)))
            elif isinstance(inner, ast.Assign):
                attributes.extend(self._attribute(target.attr, None) for target in inner.targets if isinstance(target, ast.Attribute) and self._is_self_attribute(target))
        return attributes

    def _member_assignments(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parameters: list[NormalizedParameter],
        include_constructed: bool,
    ) -> list[NormalizedMemberAssignment]:
        parameter_types = {parameter.name: parameter.type_name for parameter in parameters if parameter.type_name}
        assignments: list[NormalizedMemberAssignment] = []
        for inner in self._iter_method_nodes(node.body):
            if not isinstance(inner, (ast.Assign, ast.AnnAssign)):
                continue
            targets = inner.targets if isinstance(inner, ast.Assign) else [inner.target]
            annotation = annotation_to_str(inner.annotation) if isinstance(inner, ast.AnnAssign) else None
            for target in targets:
                if not isinstance(target, ast.Attribute) or not self._is_self_attribute(target):
                    continue
                if include_constructed and (type_name := self._call_target_name(inner.value)):
                    assignments.append(NormalizedMemberAssignment(target.attr, type_name, "constructed"))
                elif isinstance(inner.value, ast.Name) and (type_name := normalize_type_name(annotation) or parameter_types.get(inner.value.id)):
                    assignments.append(NormalizedMemberAssignment(target.attr, type_name, "supplied"))
        return assignments

    def _method_references(self, method: NormalizedMethod) -> list[NormalizedTypeReference]:
        references = [NormalizedTypeReference(parameter.type_name, "parameter") for parameter in method.parameters if parameter.type_name]
        if method.return_type:
            references.append(NormalizedTypeReference(method.return_type, "return"))
        references.extend(NormalizedTypeReference(item.class_name, "local") for item in method.local_instantiations if not item.assigned_attribute)
        return references

    def _iter_method_nodes(self, nodes: list[ast.stmt]):
        stack = list(reversed(nodes))
        while stack:
            node = stack.pop()
            yield node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.extend(reversed(list(ast.iter_child_nodes(node))))

    def _append_call(self, node: ast.Call) -> NormalizedAppendCall | None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
            and isinstance(node.func.value, ast.Attribute)
            and self._is_self_attribute(node.func.value)
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            return NormalizedAppendCall(node.func.value.attr, node.args[0].id)
        return None

    def _attribute(self, name: str, type_name: str | None, is_static: bool = False) -> NormalizedAttribute:
        return NormalizedAttribute(name, normalize_type_name(type_name), "-" if is_private(name) else "+", is_static)

    def _call_target_name(self, node: ast.AST | None) -> str | None:
        return self._resolved_name(node.func) if isinstance(node, ast.Call) else None

    def _resolved_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_self_attribute(self, node: ast.Attribute) -> bool:
        return isinstance(node.value, ast.Name) and node.value.id == "self"
