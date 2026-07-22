"""Draw.io XML rendering."""

from __future__ import annotations

from html import escape
from math import ceil
from pathlib import Path
import xml.etree.ElementTree as ET

from python2uml.model.enums import ClassKind, RelationshipType
from python2uml.model.uml_class import UMLClass
from python2uml.model.uml_diagram import UMLDiagram

CLASS_WIDTH = 240
TITLE_HEIGHT = 30
LINE_HEIGHT = 22
DIVIDER_HEIGHT = 8
MIN_COMPARTMENT_HEIGHT = 22
LEFT_MARGIN = 40
TOP_MARGIN = 40
COLUMN_GAP = 80
ROW_GAP = 80
RANK_GAP = 40
MAX_COLUMNS = 4

CLASS_STYLE = "swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;"
TEXT_STYLE = "text;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;whiteSpace=wrap;html=1;"
DIVIDER_STYLE = "line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=3;rotatable=0;labelPosition=right;points=[];portConstraint=eastwest;strokeColor=inherit;"
EDGE_STYLE = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"


class DrawioRenderer:
    def render(self, diagram: UMLDiagram, output_path: str) -> None:
        path = Path(output_path)
        if path.suffix.lower() != ".drawio":
            path = path.with_suffix(".drawio")

        root = ET.Element("mxfile", host="app.diagrams.net")
        diagram_el = ET.SubElement(root, "diagram", name="Page-1")
        graph = ET.SubElement(
            diagram_el,
            "mxGraphModel",
            {
                "dx": "1422",
                "dy": "794",
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": "827",
                "pageHeight": "1169",
                "math": "0",
                "shadow": "0",
            },
        )
        root_el = ET.SubElement(graph, "root")
        ET.SubElement(root_el, "mxCell", {"id": "0"})
        ET.SubElement(root_el, "mxCell", {"id": "1", "parent": "0"})

        positions = self._layout(diagram)
        class_ids: dict[str, str] = {}
        for index, name in enumerate(sorted(diagram.classes), start=1):
            uml_class = diagram.classes[name]
            class_id = f"class-{index}"
            class_ids[name] = class_id
            x, y = positions[name]
            attribute_height = self._compartment_height(len(uml_class.attributes))
            method_height = self._compartment_height(len(uml_class.methods))

            cell = ET.SubElement(
                root_el,
                "mxCell",
                {
                    "id": class_id,
                    "value": self._title(uml_class),
                    "style": CLASS_STYLE,
                    "vertex": "1",
                    "parent": "1",
                },
            )
            self._geometry(cell, x=x, y=y, width=CLASS_WIDTH, height=self._class_height(uml_class))
            self._child_cell(root_el, f"{class_id}-attributes", self._html_lines(self._attribute_lines(uml_class)), TEXT_STYLE, class_id, TITLE_HEIGHT, attribute_height)
            self._child_cell(root_el, f"{class_id}-divider", "", DIVIDER_STYLE, class_id, TITLE_HEIGHT + attribute_height, DIVIDER_HEIGHT)
            self._child_cell(root_el, f"{class_id}-methods", self._html_lines(self._method_lines(uml_class)), TEXT_STYLE, class_id, TITLE_HEIGHT + attribute_height + DIVIDER_HEIGHT, method_height)

        for index, relationship in enumerate(diagram.relationships, start=1):
            edge = ET.SubElement(
                root_el,
                "mxCell",
                {
                    "id": f"edge-{index}",
                    "source": class_ids.get(relationship.source, ""),
                    "target": class_ids.get(relationship.target, ""),
                    "edge": "1",
                    "parent": "1",
                    "style": self._edge_style(relationship.relationship_type),
                },
            )
            ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def _attribute_lines(self, uml_class: UMLClass) -> list[str]:
        return [f"{attribute.visibility} {attribute.name}{f': {attribute.type_name}' if attribute.type_name else ''}" for attribute in uml_class.attributes]

    def _method_lines(self, uml_class: UMLClass) -> list[str]:
        return [f"{method.visibility} {method.name}({', '.join(method.parameters)}){f': {method.return_type}' if method.return_type else ''}" for method in uml_class.methods]

    def _html_lines(self, lines: list[str]) -> str:
        return "<div>" + "<br>".join(escape(line) for line in lines) + "</div>" if lines else ""

    def _compartment_height(self, line_count: int) -> int:
        return max(MIN_COMPARTMENT_HEIGHT, line_count * LINE_HEIGHT)

    def _class_height(self, uml_class: UMLClass) -> int:
        return TITLE_HEIGHT + self._compartment_height(len(uml_class.attributes)) + DIVIDER_HEIGHT + self._compartment_height(len(uml_class.methods))

    def _title(self, uml_class: UMLClass) -> str:
        if uml_class.kind == ClassKind.CLASS:
            return escape(uml_class.name)
        return f"&lt;&lt;{escape(uml_class.kind.value)}&gt;&gt; {escape(uml_class.name)}"

    def _hierarchy_ranks(self, diagram: UMLDiagram) -> dict[str, int]:
        """Return deterministic parent-before-child ranks."""
        parents = {name: set() for name in diagram.classes}
        for relationship in diagram.relationships:
            if relationship.relationship_type in {RelationshipType.INHERITANCE, RelationshipType.IMPLEMENTATION} and relationship.source in parents and relationship.target in parents:
                parents[relationship.source].add(relationship.target)

        ranks: dict[str, int] = {}
        visiting: set[str] = set()

        def rank(name: str) -> int:
            if name in ranks:
                return ranks[name]
            if name in visiting:
                return 0
            visiting.add(name)
            ranks[name] = 1 + max((rank(parent) for parent in sorted(parents[name])), default=-1)
            visiting.remove(name)
            return ranks[name]

        return {name: rank(name) for name in sorted(diagram.classes)}

    def _layout(self, diagram: UMLDiagram) -> dict[str, tuple[int, int]]:
        ranks = self._hierarchy_ranks(diagram)
        names_by_rank: dict[int, list[str]] = {}
        for name, rank in ranks.items():
            names_by_rank.setdefault(rank, []).append(name)

        positions: dict[str, tuple[int, int]] = {}
        y = TOP_MARGIN
        for rank in sorted(names_by_rank):
            names = sorted(names_by_rank[rank])
            for chunk_index in range(ceil(len(names) / MAX_COLUMNS)):
                chunk = names[chunk_index * MAX_COLUMNS : (chunk_index + 1) * MAX_COLUMNS]
                for column, name in enumerate(chunk):
                    positions[name] = (LEFT_MARGIN + column * (CLASS_WIDTH + COLUMN_GAP), y)
                y += max(self._class_height(diagram.classes[name]) for name in chunk) + ROW_GAP
            y += RANK_GAP
        return positions

    def _child_cell(self, root: ET.Element, cell_id: str, value: str, style: str, parent: str, y: int, height: int) -> None:
        cell = ET.SubElement(root, "mxCell", {"id": cell_id, "value": value, "style": style, "vertex": "1", "parent": parent})
        self._geometry(cell, x=0, y=y, width=CLASS_WIDTH, height=height)

    def _geometry(self, cell: ET.Element, *, x: int, y: int, width: int, height: int) -> None:
        ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(width), "height": str(height), "as": "geometry"})

    def _edge_style(self, relationship_type: RelationshipType) -> str:
        return (
            EDGE_STYLE
            + {
                RelationshipType.INHERITANCE: "endArrow=block;endFill=0;",
                RelationshipType.IMPLEMENTATION: "endArrow=block;endFill=0;dashed=1;",
                RelationshipType.ASSOCIATION: "endArrow=open;",
                RelationshipType.AGGREGATION: "startArrow=diamond;startFill=0;endArrow=none;",
                RelationshipType.COMPOSITION: "startArrow=diamond;startFill=1;endArrow=none;",
            }[relationship_type]
        )
