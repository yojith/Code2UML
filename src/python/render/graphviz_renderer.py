"""Graphviz rendering."""

from __future__ import annotations

from pathlib import Path

from graphviz import Digraph

from model.enums import RelationshipType
from model.uml_class import UMLClass
from model.uml_diagram import UMLDiagram

GRAPH_ATTRS = {
    "splines": "ortho",
    "overlap": "false",
    "newrank": "true",
    "nodesep": "1.2",
    "ranksep": "1.6",
    "pad": "0.4",
}


class GraphvizRenderer:
    def create_dot(self) -> Digraph:
        return Digraph(comment="UML Diagram", graph_attr=GRAPH_ATTRS)

    def render(self, diagram: UMLDiagram, output_path: str, file_extension: str = "svg") -> None:
        dot = self.create_dot()

        for uml_class in diagram.classes.values():
            dot.node(uml_class.name, shape="plaintext", label=self._class_label(uml_class), margin="0")

        for relationship in diagram.relationships:
            attrs = self._edge_attrs(relationship.relationship_type)
            dot.edge(relationship.source, relationship.target, **attrs)

        output = Path(output_path)
        if output.suffix:
            file_extension = output.suffix.lstrip(".")
            output_path = str(output.with_suffix(""))

        dot.render(output_path, format=file_extension, cleanup=True)

    def _class_label(self, uml_class: UMLClass) -> str:
        attribute_lines = ""
        for attribute in uml_class.attributes:
            type_suffix = f": {attribute.type_name}" if attribute.type_name else ""
            attribute_lines += f'{attribute.visibility} {attribute.name}{type_suffix}<BR ALIGN="LEFT"/>'

        method_lines = ""
        for method in uml_class.methods:
            parameters = ", ".join(method.parameters)
            return_suffix = f": {method.return_type}" if method.return_type else ""
            method_lines += f'{method.visibility} {method.name}({parameters}){return_suffix}<BR ALIGN="LEFT"/>'

        return f"""<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6">
        <TR><TD>{uml_class.name}</TD></TR>
        <TR><TD ALIGN="LEFT">{attribute_lines}</TD></TR>
        <TR><TD ALIGN="LEFT">{method_lines}</TD></TR>
        </TABLE>>"""

    def _edge_attrs(self, relationship_type: RelationshipType) -> dict[str, str]:
        return {
            RelationshipType.INHERITANCE: {"arrowhead": "onormal"},
            RelationshipType.ASSOCIATION: {"arrowhead": "normal"},
            RelationshipType.AGGREGATION: {"arrowtail": "odiamond", "dir": "back"},
            RelationshipType.COMPOSITION: {"arrowtail": "diamond", "dir": "back"},
        }[relationship_type]
