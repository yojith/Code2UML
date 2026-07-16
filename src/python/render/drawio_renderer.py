"""Draw.io XML rendering."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

from model.enums import ClassKind, RelationshipType
from model.uml_class import UMLClass
from model.uml_diagram import UMLDiagram


class DrawioRenderer:
    def render(self, diagram: UMLDiagram, output_path: str) -> None:
        path = Path(output_path)
        if path.suffix.lower() != ".drawio":
            path = path.with_suffix(".drawio")

        root = ET.Element("mxfile", host="app.diagrams.net")
        diagram_el = ET.SubElement(root, "diagram", name="Page-1")
        graph = ET.SubElement(diagram_el, "mxGraphModel")
        root_el = ET.SubElement(graph, "root")

        ET.SubElement(root_el, "mxCell", {"id": "0"})
        ET.SubElement(root_el, "mxCell", {"id": "1", "parent": "0"})

        positions = self._layout(diagram)
        for index, uml_class in enumerate(diagram.classes.values(), start=2):
            x, y = positions[uml_class.name]
            cell = ET.SubElement(
                root_el,
                "mxCell",
                {
                    "id": str(index),
                    "value": self._label(uml_class),
                    "style": "rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
                    "vertex": "1",
                    "parent": "1",
                },
            )
            ET.SubElement(
                cell,
                "mxGeometry",
                {
                    "x": str(x),
                    "y": str(y),
                    "width": "220",
                    "height": "140",
                    "as": "geometry",
                },
            )
        current_id = len(diagram.classes) + 2
        lookup = {name: str(i + 2) for i, name in enumerate(diagram.classes)}

        for relationship in diagram.relationships:
            edge = ET.SubElement(
                root_el,
                "mxCell",
                {
                    "id": str(current_id),
                    "source": lookup.get(relationship.source, ""),
                    "target": lookup.get(relationship.target, ""),
                    "edge": "1",
                    "parent": "1",
                    "style": self._edge_style(relationship.relationship_type),
                },
            )
            ET.SubElement(
                edge,
                "mxGeometry",
                {
                    "relative": "1",
                    "as": "geometry",
                },
            )
            current_id += 1

        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

    def _layout(self, diagram: UMLDiagram) -> dict[str, tuple[int, int]]:
        positions: dict[str, tuple[int, int]] = {}
        for index, name in enumerate(diagram.classes):
            positions[name] = (40 + (index % 3) * 280, 40 + (index // 3) * 220)
        return positions

    def _label(self, uml_class: UMLClass) -> str:
        title = uml_class.name if uml_class.kind == ClassKind.CLASS else f"<<{uml_class.kind.value}>> {uml_class.name}"
        lines = [title]
        for attribute in uml_class.attributes:
            lines.append(f"{attribute.visibility} {attribute.name}")
        for method in uml_class.methods:
            lines.append(f"{method.visibility} {method.name}({', '.join(method.parameters)})")
        return "\\n".join(lines)

    def _edge_style(self, relationship_type: RelationshipType) -> str:
        return {
            RelationshipType.INHERITANCE: "endArrow=block;endFill=0;",
            RelationshipType.IMPLEMENTATION: "endArrow=block;endFill=0;dashed=1;",
            RelationshipType.ASSOCIATION: "endArrow=open;",
            RelationshipType.AGGREGATION: "startArrow=diamond;startFill=0;endArrow=none;",
            RelationshipType.COMPOSITION: "startArrow=diamond;startFill=1;endArrow=none;",
        }[relationship_type]
