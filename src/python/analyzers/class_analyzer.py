"""Class extraction from AST."""

from __future__ import annotations

import ast

from model.uml_attribute import UMLAttribute
from model.uml_class import UMLClass
from model.uml_diagram import UMLDiagram
from model.uml_method import UMLMethod
from utils.ast_utils import annotation_to_str, is_private
from utils.type_resolver import normalize_type_name


class ClassAnalyzer:
    def analyze(self, ast_trees: list[ast.AST]) -> UMLDiagram:
        diagram = UMLDiagram()
        for tree in ast_trees:
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    diagram.classes[node.name] = self._analyze_class(node)
        return diagram

    def _analyze_class(self, node: ast.ClassDef) -> UMLClass:
        attributes: list[UMLAttribute] = []
        methods: list[UMLMethod] = []
        seen_attributes: set[str] = set()
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef):
                visibility = "-" if is_private(body_item.name) else "+"
                if body_item.name == "__init__":
                    visibility = "+"
                parameters = [self._format_parameter(arg) for arg in body_item.args.args if arg.arg != "self"]
                methods.append(
                    UMLMethod(
                        name=body_item.name,
                        parameters=parameters,
                        return_type=annotation_to_str(body_item.returns),
                        visibility=visibility,
                    )
                )
                for attribute in self._attributes_from_method(body_item):
                    if attribute.name not in seen_attributes:
                        seen_attributes.add(attribute.name)
                        attributes.append(attribute)
        return UMLClass(name=node.name, attributes=attributes, methods=methods)

    def _format_parameter(self, arg: ast.arg) -> str:
        type_name = annotation_to_str(arg.annotation)
        return f"{arg.arg}: {type_name}" if type_name else arg.arg

    def _attributes_from_method(self, node: ast.FunctionDef) -> list[UMLAttribute]:
        attributes: list[UMLAttribute] = []
        for inner in self._iter_method_nodes(node.body):
            if isinstance(inner, ast.AnnAssign) and isinstance(inner.target, ast.Attribute) and self._is_self_attr(inner.target):
                attributes.append(self._attribute_from_target(inner.target.attr, inner.annotation))
            elif isinstance(inner, ast.Assign):
                for target in inner.targets:
                    if isinstance(target, ast.Attribute) and self._is_self_attr(target):
                        attributes.append(self._attribute_from_target(target.attr, None))
        return attributes

    def _iter_method_nodes(self, nodes: list[ast.stmt]) -> list[ast.AST]:
        stack = list(reversed(nodes))
        while stack:
            node = stack.pop()
            yield node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            stack.extend(reversed(list(ast.iter_child_nodes(node))))

    def _attribute_from_target(self, name: str, annotation: ast.AST | None) -> UMLAttribute:
        return UMLAttribute(
            name=name,
            type_name=normalize_type_name(annotation_to_str(annotation)),
            visibility="-" if is_private(name) else "+",
        )

    def _is_self_attr(self, node: ast.Attribute) -> bool:
        return isinstance(node.value, ast.Name) and node.value.id == "self"
