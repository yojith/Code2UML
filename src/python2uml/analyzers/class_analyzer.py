"""Class extraction from normalized AST."""

from __future__ import annotations

from model.uml_attribute import UMLAttribute
from model.uml_class import UMLClass
from model.uml_diagram import UMLDiagram
from model.uml_method import UMLMethod
from parser.normalized_ast import NormalizedModule


class ClassAnalyzer:
    def analyze(self, modules: list[NormalizedModule]) -> UMLDiagram:
        diagram = UMLDiagram()
        for module in modules:
            for normalized_class in module.classes:
                diagram.classes[normalized_class.name] = self._analyze_class(normalized_class)
        return diagram

    def _analyze_class(self, normalized_class) -> UMLClass:
        return UMLClass(
            name=normalized_class.name,
            kind=normalized_class.kind,
            attributes=[self._attribute_from_normalized(attribute) for attribute in normalized_class.attributes],
            methods=[self._method_from_normalized(method) for method in normalized_class.methods],
        )

    def _attribute_from_normalized(self, attribute) -> UMLAttribute:
        return UMLAttribute(
            name=attribute.name,
            type_name=attribute.type_name,
            visibility=attribute.visibility,
        )

    def _method_from_normalized(self, method) -> UMLMethod:
        return UMLMethod(
            name=method.name,
            parameters=[f"{parameter.name}: {parameter.type_name}" if parameter.type_name else parameter.name for parameter in method.parameters],
            return_type=method.return_type,
            visibility=method.visibility,
        )
