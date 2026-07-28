"""Draw.io XML rendering."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from math import isclose, isfinite
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from python2uml.model.enums import ClassKind, RelationshipType
from python2uml.model.uml_class import UMLClass
from python2uml.model.uml_diagram import UMLDiagram
from python2uml.renderers.graphviz_renderer import get_dot_executable

CLASS_WIDTH = 240
TITLE_HEIGHT = 30
LINE_HEIGHT = 22
DIVIDER_HEIGHT = 8
MIN_COMPARTMENT_HEIGHT = 22

CLASS_STYLE = "swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;"
TEXT_STYLE = "text;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;whiteSpace=wrap;html=1;"
DIVIDER_STYLE = "line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=3;rotatable=0;labelPosition=right;points=[];portConstraint=eastwest;strokeColor=inherit;"
EDGE_STYLE = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"

Point = tuple[float, float]
Rectangle = tuple[float, float, float, float]


@dataclass(frozen=True, slots=True)
class EdgeRoute:
    source: Point
    target: Point
    points: tuple[Point, ...]


@dataclass(frozen=True, slots=True)
class LayoutResult:
    nodes: dict[str, Rectangle]
    routes: tuple[EdgeRoute, ...]


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

        layout = self._layout(diagram)
        class_ids: dict[str, str] = {}
        for index, name in enumerate(sorted(diagram.classes), start=1):
            uml_class = diagram.classes[name]
            class_id = f"class-{index}"
            class_ids[name] = class_id
            x, y, width, height = layout.nodes[name]
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
            self._geometry(cell, x=x, y=y, width=width, height=height)
            self._child_cell(root_el, f"{class_id}-attributes", self._html_lines(self._attribute_lines(uml_class)), TEXT_STYLE, class_id, TITLE_HEIGHT, attribute_height)
            self._child_cell(root_el, f"{class_id}-divider", "", DIVIDER_STYLE, class_id, TITLE_HEIGHT + attribute_height, DIVIDER_HEIGHT)
            self._child_cell(root_el, f"{class_id}-methods", self._html_lines(self._method_lines(uml_class)), TEXT_STYLE, class_id, TITLE_HEIGHT + attribute_height + DIVIDER_HEIGHT, method_height)

        for index, (relationship, route) in enumerate(zip(diagram.relationships, layout.routes, strict=True), start=1):
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
            geometry = ET.SubElement(edge, "mxGeometry", {"relative": "1", "as": "geometry"})
            self._point(geometry, route.source, "sourcePoint")
            self._point(geometry, route.target, "targetPoint")
            if route.points:
                points = ET.SubElement(geometry, "Array", {"as": "points"})
                for point in route.points:
                    self._point(points, point)

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

    def _layout(self, diagram: UMLDiagram) -> LayoutResult:
        names = sorted(diagram.classes)
        node_ids = {name: f"node_{index}" for index, name in enumerate(names, start=1)}
        layout = self._run_layout(self._dot_source(diagram, node_ids))
        min_x, min_y, max_x, max_y = self._numbers(layout.get("bb"), 4, "bounding box")
        if max_x < min_x or max_y < min_y:
            raise RuntimeError("Graphviz layout returned an invalid bounding box.")

        objects = layout.get("objects")
        if not isinstance(objects, list):
            raise RuntimeError("Graphviz layout returned invalid node geometry.")
        centers: dict[str, Point] = {}
        names_by_gvid: dict[int, str] = {}
        expected_ids = set(node_ids.values())
        for item in objects:
            if not isinstance(item, dict) or not isinstance(item.get("_gvid"), int) or isinstance(item.get("_gvid"), bool) or not isinstance(item.get("name"), str):
                raise RuntimeError("Graphviz layout returned invalid node geometry.")
            gvid = item["_gvid"]
            node_id = item["name"]
            names_by_gvid[gvid] = node_id
            if node_id in expected_ids:
                if node_id in centers:
                    raise RuntimeError(f"Graphviz layout returned duplicate node geometry for {node_id}.")
                centers[node_id] = self._point_numbers(item.get("pos"), "node position")

        missing = sorted(expected_ids - centers.keys())
        if missing:
            raise RuntimeError(f"Graphviz layout is missing node geometry for: {', '.join(missing)}.")

        nodes: dict[str, Rectangle] = {}
        for name in names:
            center_x, center_y = centers[node_ids[name]]
            height = self._class_height(diagram.classes[name])
            nodes[name] = (center_x - min_x - CLASS_WIDTH / 2, max_y - center_y - height / 2, CLASS_WIDTH, height)

        edges = layout.get("edges", [])
        if not isinstance(edges, list) or len(edges) != len(diagram.relationships):
            raise RuntimeError("Graphviz layout returned the wrong number of edge routes.")

        routes: list[EdgeRoute] = []
        for index, (relationship, edge) in enumerate(zip(diagram.relationships, edges, strict=True), start=1):
            if not isinstance(edge, dict):
                raise RuntimeError(f"Graphviz layout returned invalid edge route {index}.")
            expected_tail = node_ids.get(relationship.source)
            expected_head = node_ids.get(relationship.target)
            if expected_tail is None or expected_head is None:
                raise RuntimeError("Draw.io layout relationships must have project-local endpoints.")
            if names_by_gvid.get(edge.get("tail")) != expected_tail or names_by_gvid.get(edge.get("head")) != expected_head:
                raise RuntimeError(f"Graphviz layout returned mismatched edge route {index}.")
            routes.append(self._edge_route(edge.get("pos"), min_x, max_y, index))

        return LayoutResult(nodes=nodes, routes=tuple(routes))

    def _dot_source(self, diagram: UMLDiagram, node_ids: dict[str, str]) -> str:
        lines = ["digraph drawio_layout {", "  graph [splines=ortho];", "  edge [dir=none];"]
        for name in sorted(diagram.classes):
            width = CLASS_WIDTH / 72
            height = self._class_height(diagram.classes[name]) / 72
            lines.append(f"  {node_ids[name]} [shape=box, fixedsize=true, width={width:.6f}, height={height:.6f}];")
        for relationship in diagram.relationships:
            try:
                source = node_ids[relationship.source]
                target = node_ids[relationship.target]
            except KeyError as error:
                raise RuntimeError(f"Draw.io layout relationship endpoint is not project-local: {error.args[0]}.") from error
            lines.append(f"  {source} -> {target};")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _run_layout(self, dot_source: str) -> dict[str, object]:
        executable = get_dot_executable()
        try:
            completed = subprocess.run([str(executable), "-Tjson"], input=dot_source, text=True, capture_output=True, check=True)
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() if error.stderr else str(error)
            raise RuntimeError(f"Graphviz draw.io layout failed: {detail}") from error
        except OSError as error:
            raise RuntimeError(f"Graphviz draw.io layout failed: {error}") from error

        try:
            layout = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise RuntimeError("Graphviz layout returned invalid JSON.") from error
        if not isinstance(layout, dict):
            raise RuntimeError("Graphviz layout JSON must be one object.")
        return layout

    def _edge_route(self, value: object, min_x: float, max_y: float, index: int) -> EdgeRoute:
        if not isinstance(value, str):
            raise RuntimeError(f"Graphviz layout returned unusable edge route {index}.")
        markers: dict[str, Point] = {}
        points: list[Point] = []
        for token in value.replace(";", " ").split():
            parts = token.split(",")
            if len(parts) == 3 and parts[0] in {"s", "e"}:
                markers[parts[0]] = self._coordinate(parts[1], parts[2], f"edge route {index}")
            elif len(parts) == 2:
                points.append(self._coordinate(parts[0], parts[1], f"edge route {index}"))
            else:
                raise RuntimeError(f"Graphviz layout returned unusable edge route {index}.")

        raw_route = ([markers["s"]] if "s" in markers else []) + points + ([markers["e"]] if "e" in markers else [])
        transformed = [(x - min_x, max_y - y) for x, y in raw_route]
        route: list[Point] = []
        for point in transformed:
            if not route:
                route.append(point)
                continue
            previous = route[-1]
            if isclose(previous[0], point[0], abs_tol=1e-6):
                point = (previous[0], point[1])
            elif isclose(previous[1], point[1], abs_tol=1e-6):
                point = (point[0], previous[1])
            else:
                raise RuntimeError(f"Graphviz layout returned non-orthogonal edge route {index}.")
            if point == previous:
                continue
            if len(route) > 1 and (route[-2][0] == previous[0] == point[0] or route[-2][1] == previous[1] == point[1]):
                route[-1] = point
            else:
                route.append(point)

        if len(route) < 2:
            raise RuntimeError(f"Graphviz layout returned unusable edge route {index}.")
        return EdgeRoute(source=route[0], target=route[-1], points=tuple(route[1:-1]))

    def _numbers(self, value: object, count: int, label: str) -> tuple[float, ...]:
        if not isinstance(value, str):
            raise RuntimeError(f"Graphviz layout returned an invalid {label}.")
        parts = value.split(",")
        if len(parts) != count:
            raise RuntimeError(f"Graphviz layout returned an invalid {label}.")
        try:
            numbers = tuple(float(part) for part in parts)
        except ValueError as error:
            raise RuntimeError(f"Graphviz layout returned an invalid {label}.") from error
        if not all(isfinite(number) for number in numbers):
            raise RuntimeError(f"Graphviz layout returned an invalid {label}.")
        return numbers

    def _point_numbers(self, value: object, label: str) -> Point:
        x, y = self._numbers(value, 2, label)
        return x, y

    def _coordinate(self, x: str, y: str, label: str) -> Point:
        return self._point_numbers(f"{x},{y}", label)

    def _child_cell(self, root: ET.Element, cell_id: str, value: str, style: str, parent: str, y: int, height: int) -> None:
        cell = ET.SubElement(root, "mxCell", {"id": cell_id, "value": value, "style": style, "vertex": "1", "parent": parent})
        self._geometry(cell, x=0, y=y, width=CLASS_WIDTH, height=height)

    def _geometry(self, cell: ET.Element, *, x: float, y: float, width: float, height: float) -> None:
        ET.SubElement(
            cell,
            "mxGeometry",
            {"x": self._number(x), "y": self._number(y), "width": self._number(width), "height": self._number(height), "as": "geometry"},
        )

    def _point(self, parent: ET.Element, point: Point, point_type: str | None = None) -> None:
        attributes = {"x": self._number(point[0]), "y": self._number(point[1])}
        if point_type:
            attributes["as"] = point_type
        ET.SubElement(parent, "mxPoint", attributes)

    def _number(self, value: float) -> str:
        if isclose(value, 0, abs_tol=5e-7):
            value = 0
        return f"{value:.6f}".rstrip("0").rstrip(".")

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
