import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import xml.etree.ElementTree as ET

import pytest

from python2uml.model.enums import ClassKind, RelationshipType
from python2uml.model.uml_attribute import UMLAttribute
from python2uml.model.uml_class import UMLClass
from python2uml.model.uml_diagram import UMLDiagram
from python2uml.model.uml_method import UMLMethod
from python2uml.model.uml_relationship import UMLRelationship
from python2uml.renderers.drawio_renderer import DrawioRenderer
from python2uml.renderers.graphviz_renderer import GraphvizRenderer, get_dot_executable


BUNDLED_DOT = Path("C:/python2uml/graphviz/bin/dot.exe")


def diagram_with_every_style() -> UMLDiagram:
    classes = {kind.value: UMLClass(kind.value, kind=kind) for kind in ClassKind}
    relationships = [
        UMLRelationship(ClassKind.CLASS.value, kind.value, relationship_type)
        for kind, relationship_type in zip(
            list(ClassKind)[1:],
            RelationshipType,
            strict=False,
        )
    ]
    return UMLDiagram(classes=classes, relationships=relationships)


def drawio_cells(path: Path) -> dict[str, ET.Element]:
    return {cell.get("id"): cell for cell in ET.parse(path).getroot().findall(".//mxCell")}


def graphviz_layout_json(
    diagram: UMLDiagram,
    *,
    bb: str = "0,0,1200,1200",
    positions: dict[str, str] | None = None,
    routes: list[str] | None = None,
) -> dict[str, object]:
    names = sorted(diagram.classes)
    node_indexes = {name: index for index, name in enumerate(names)}
    positions = positions or {name: f"{160 + index * 260},{1100 - index * 140}" for index, name in enumerate(names)}
    routes = routes or [f"{80 + index * 20},900 {80 + index * 20},800" for index in range(len(diagram.relationships))]
    renderer = DrawioRenderer()
    return {
        "name": "drawio_layout",
        "directed": True,
        "strict": False,
        "_draw_": [],
        "bb": bb,
        "xdotversion": "1.7",
        "_subgraph_cnt": 0,
        "objects": [
            {
                "_gvid": index,
                "name": f"node_{index + 1}",
                "_draw_": [],
                "_ldraw_": [],
                "fixedsize": "true",
                "height": f"{renderer._class_height(diagram.classes[name]) / 72:.4f}",
                "label": f"node_{index + 1}",
                "pos": positions[name],
                "shape": "box",
                "width": f"{240 / 72:.4f}",
            }
            for index, name in enumerate(names)
        ],
        "edges": [
            {
                "_gvid": index,
                "tail": node_indexes[relationship.source],
                "head": node_indexes[relationship.target],
                "_draw_": [],
                "dir": "none",
                "pos": routes[index],
            }
            for index, relationship in enumerate(diagram.relationships)
        ],
    }


def graphviz_result(layout: dict[str, object] | str) -> subprocess.CompletedProcess[str]:
    stdout = layout if isinstance(layout, str) else json.dumps(layout)
    return subprocess.CompletedProcess([str(BUNDLED_DOT), "-Tjson"], 0, stdout, "")


def render_drawio_with_layout(diagram: UMLDiagram, output: Path, layout: dict[str, object] | None = None):
    with (
        patch("python2uml.renderers.drawio_renderer.get_dot_executable", return_value=BUNDLED_DOT),
        patch("python2uml.renderers.drawio_renderer.subprocess.run", return_value=graphviz_result(layout or graphviz_layout_json(diagram))) as run,
    ):
        DrawioRenderer().render(diagram, str(output))
    return run


def test_graphviz_requires_bundled_dot(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("EXTENSION_GRAPHVIZ_DOT", raising=False)
    with pytest.raises(RuntimeError, match="was not supplied"):
        get_dot_executable()

    monkeypatch.setenv("EXTENSION_GRAPHVIZ_DOT", "dot.exe")
    with pytest.raises(RuntimeError, match="absolute"):
        get_dot_executable()

    missing = tmp_path / "graphviz" / "bin" / "dot.exe"
    monkeypatch.setenv("EXTENSION_GRAPHVIZ_DOT", str(missing))
    with pytest.raises(RuntimeError, match="was not found"):
        get_dot_executable()


def test_graphviz_requires_path_to_resolve_the_configured_dot(monkeypatch, tmp_path: Path):
    configured = tmp_path / "graphviz" / "bin" / "dot.exe"
    configured.parent.mkdir(parents=True)
    configured.write_bytes(b"")
    other = tmp_path / "system" / "dot.exe"
    other.parent.mkdir()
    other.write_bytes(b"")
    monkeypatch.setenv("EXTENSION_GRAPHVIZ_DOT", str(configured))

    with patch("python2uml.renderers.graphviz_renderer.shutil.which", return_value=str(other)), pytest.raises(RuntimeError, match="does not match"):
        get_dot_executable()
    with patch("python2uml.renderers.graphviz_renderer.shutil.which", return_value=str(configured)):
        assert get_dot_executable() == configured.resolve()


def test_graphviz_source_maps_every_class_kind_and_relationship_style():
    renderer = GraphvizRenderer()
    dot = renderer.create_dot()

    with patch.object(renderer, "create_dot", return_value=dot), patch("python2uml.renderers.graphviz_renderer.get_dot_executable"), patch.object(dot, "render"):
        renderer.render(diagram_with_every_style(), "out.svg")

    for kind in ClassKind:
        expected_title = kind.value if kind == ClassKind.CLASS else f"&lt;&lt;{kind.value}&gt;&gt; {kind.value}"
        assert expected_title in dot.source
    for expected in (
        "arrowhead=onormal",
        "arrowhead=vee style=dashed",
        "arrowhead=normal",
        "arrowtail=odiamond dir=back",
        "arrowtail=diamond dir=back",
    ):
        assert expected in dot.source


def test_drawio_xml_maps_every_class_kind_and_relationship_style(tmp_path: Path):
    output = tmp_path / "diagram.drawio"
    diagram = diagram_with_every_style()

    render_drawio_with_layout(diagram, output)

    cells = drawio_cells(output)
    classes = [cell for cell in cells.values() if cell.get("vertex") == "1" and cell.get("parent") == "1"]
    styles = [cell.get("style") for cell in cells.values() if cell.get("edge") == "1"]

    assert len(classes) == len(ClassKind)
    assert {cell.get("value") for cell in classes} == {kind.value if kind == ClassKind.CLASS else f"&lt;&lt;{kind.value}&gt;&gt; {kind.value}" for kind in ClassKind}
    for expected in (
        "endArrow=block;endFill=0;",
        "endArrow=open;dashed=1;",
        "endArrow=open;",
        "startArrow=diamond;startFill=0;endArrow=none;",
        "startArrow=diamond;startFill=1;endArrow=none;",
    ):
        assert any("edgeStyle=orthogonalEdgeStyle" in style and expected in style for style in styles)


def test_graphviz_source_escapes_dynamic_html_label_text():
    renderer = GraphvizRenderer()
    dot = renderer.create_dot()
    uml_class = UMLClass(
        "Box<T>&",
        kind=ClassKind.INTERFACE,
        attributes=[UMLAttribute("items<&>", "List<Order>&")],
        methods=[UMLMethod("find<&>", ["key: Map<K, V>&"], "Result<T>&")],
    )

    with patch.object(renderer, "create_dot", return_value=dot), patch("python2uml.renderers.graphviz_renderer.get_dot_executable"), patch.object(dot, "render"):
        renderer.render(UMLDiagram(classes={uml_class.name: uml_class}), "out.svg")

    assert "&lt;&lt;interface&gt;&gt; Box&lt;T&gt;&amp;" in dot.source
    assert "items&lt;&amp;&gt;: List&lt;Order&gt;&amp;" in dot.source
    assert "find&lt;&amp;&gt;(key: Map&lt;K, V&gt;&amp;): Result&lt;T&gt;&amp;" in dot.source


def test_drawio_xml_uses_escaped_uml_compartments_without_literal_newlines(tmp_path: Path):
    output = tmp_path / "diagram.drawio"
    uml_class = UMLClass(
        "Repository",
        attributes=[UMLAttribute("items<&>", "List<Order>&"), UMLAttribute("cache", "dict[str, Order]")],
        methods=[UMLMethod("find<&>", ["id: Map<K, V>&"], "Order<&>"), UMLMethod("save", ["order: Order"])],
    )

    diagram = UMLDiagram(classes={uml_class.name: uml_class})
    render_drawio_with_layout(diagram, output)

    cells = drawio_cells(output)
    parent = next(cell for cell in cells.values() if cell.get("vertex") == "1" and cell.get("parent") == "1")
    children = [cell for cell in cells.values() if cell.get("parent") == parent.get("id")]

    assert "swimlane" in parent.get("style", "")
    assert len(children) == 3
    assert all("\\n" not in cell.get("value", "") for cell in cells.values())
    assert any("items&lt;&amp;&gt;: List&lt;Order&gt;&amp;" in cell.get("value", "") for cell in children)
    assert any("find&lt;&amp;&gt;(id: Map&lt;K, V&gt;&amp;): Order&lt;&amp;&gt;" in cell.get("value", "") for cell in children)


def test_drawio_xml_escapes_titles_and_grows_for_compartments(tmp_path: Path):
    output = tmp_path / "diagram.drawio"
    uml_class = UMLClass(
        "Box<T>&",
        attributes=[UMLAttribute("items", "List<Order>"), UMLAttribute("cache", "dict[str, Order]")],
        methods=[UMLMethod("find", ["id: int"], "Order")],
    )

    diagram = UMLDiagram(classes={uml_class.name: uml_class})
    render_drawio_with_layout(diagram, output)

    parent = next(cell for cell in drawio_cells(output).values() if cell.get("vertex") == "1" and cell.get("parent") == "1")
    assert "Box&lt;T&gt;&amp;" in parent.get("value", "")
    assert float(parent.find("mxGeometry").get("height")) > 86


def test_drawio_xml_is_deterministic(tmp_path: Path):
    diagram = diagram_with_every_style()
    first = tmp_path / "first.drawio"
    second = tmp_path / "second.drawio"

    render_drawio_with_layout(diagram, first)
    render_drawio_with_layout(diagram, second)

    assert first.read_bytes() == second.read_bytes()


def test_drawio_uses_graphviz_node_rectangles_and_real_class_dimensions(tmp_path: Path):
    short = UMLClass("Short")
    tall = UMLClass("Tall", attributes=[UMLAttribute(f"field_{index}") for index in range(3)])
    diagram = UMLDiagram(classes={tall.name: tall, short.name: short})
    output = tmp_path / "diagram.drawio"
    layout = graphviz_layout_json(diagram, bb="0,0,600,400", positions={"Short": "180,300", "Tall": "360,150"})

    run = render_drawio_with_layout(diagram, output, layout)

    geometry_by_title = {cell.get("value"): cell.find("mxGeometry") for cell in drawio_cells(output).values() if cell.get("vertex") == "1" and cell.get("parent") == "1"}
    assert {key: float(value) for key, value in geometry_by_title["Short"].items() if key in {"x", "y", "width", "height"}} == {"x": 60, "y": 59, "width": 240, "height": 82}
    assert {key: float(value) for key, value in geometry_by_title["Tall"].items() if key in {"x", "y", "width", "height"}} == {"x": 240, "y": 187, "width": 240, "height": 126}

    dot_source = run.call_args.kwargs["input"]
    assert "node_1 [shape=box, fixedsize=true, width=3.333333, height=1.138889];" in dot_source
    assert "node_2 [shape=box, fixedsize=true, width=3.333333, height=1.750000];" in dot_source
    run.assert_called_once_with([str(BUNDLED_DOT), "-Tjson"], input=dot_source, text=True, capture_output=True, check=True)


def test_drawio_layout_edges_ignore_relationship_type_but_xml_styles_do_not(tmp_path: Path):
    dot_sources = []
    expected_styles = {
        RelationshipType.INHERITANCE: "endArrow=block;endFill=0;",
        RelationshipType.IMPLEMENTATION: "endArrow=open;dashed=1;",
        RelationshipType.ASSOCIATION: "endArrow=open;",
        RelationshipType.AGGREGATION: "startArrow=diamond;startFill=0;endArrow=none;",
        RelationshipType.COMPOSITION: "startArrow=diamond;startFill=1;endArrow=none;",
    }
    for relationship_type in RelationshipType:
        diagram = UMLDiagram(
            classes={name: UMLClass(name) for name in ("Source", "Target")},
            relationships=[UMLRelationship("Source", "Target", relationship_type)],
        )
        output = tmp_path / f"{relationship_type.value}.drawio"

        run = render_drawio_with_layout(diagram, output)

        dot_sources.append(run.call_args.kwargs["input"])
        edge = next(cell for cell in drawio_cells(output).values() if cell.get("edge") == "1")
        assert expected_styles[relationship_type] in edge.get("style", "")

    assert len(set(dot_sources)) == 1


def test_drawio_serializes_orthogonal_graphviz_route_without_endpoint_waypoints(tmp_path: Path):
    diagram = UMLDiagram(
        classes={name: UMLClass(name) for name in ("Source", "Target")},
        relationships=[UMLRelationship("Source", "Target", RelationshipType.ASSOCIATION)],
    )
    output = tmp_path / "diagram.drawio"
    layout = graphviz_layout_json(
        diagram,
        bb="0,0,400,400",
        positions={"Source": "60,341", "Target": "140,159"},
        routes=["60,300 60,280 60,260 60,260 60,260 140,260 140,260 140,260 140,220 140,200"],
    )

    render_drawio_with_layout(diagram, output, layout)

    cells = drawio_cells(output)
    edge = next(cell for cell in cells.values() if cell.get("edge") == "1")
    geometry = edge.find("mxGeometry")
    points = geometry.findall("Array[@as='points']/mxPoint")
    style = dict(part.split("=", 1) for part in edge.get("style", "").split(";") if "=" in part)
    effective_endpoints = []
    for terminal, prefix in (("source", "exit"), ("target", "entry")):
        terminal_geometry = cells[edge.get(terminal)].find("mxGeometry")
        effective_endpoints.append(
            (
                float(terminal_geometry.get("x")) + float(terminal_geometry.get("width")) * float(style[f"{prefix}X"]),
                float(terminal_geometry.get("y")) + float(terminal_geometry.get("height")) * float(style[f"{prefix}Y"]),
            )
        )

    assert effective_endpoints == [(60, 100), (140, 200)]
    assert [(float(point.get("x")), float(point.get("y"))) for point in points] == [(60, 140), (140, 140)]


def test_drawio_keeps_parallel_routes_separate_and_serializes_self_loops(tmp_path: Path):
    diagram = UMLDiagram(
        classes={name: UMLClass(name) for name in ("A", "B")},
        relationships=[
            UMLRelationship("A", "B", RelationshipType.ASSOCIATION),
            UMLRelationship("A", "B", RelationshipType.COMPOSITION),
            UMLRelationship("B", "B", RelationshipType.AGGREGATION),
        ],
    )
    output = tmp_path / "diagram.drawio"
    layout = graphviz_layout_json(
        diagram,
        bb="0,0,276,362",
        positions={"A": "138,321", "B": "138,181"},
        routes=[
            "198,280 198,222",
            "138,280 138,222",
            "18,182 0,182 0,102 98,102 98,140",
        ],
    )

    render_drawio_with_layout(diagram, output, layout)

    cells = drawio_cells(output)
    edges = [cells[f"edge-{index}"] for index in range(1, 4)]
    for edge in edges:
        geometry = edge.find("mxGeometry")
        assert geometry.find("mxPoint[@as='sourcePoint']") is None
        assert geometry.find("mxPoint[@as='targetPoint']") is None

    effective_endpoints = []
    for edge in edges[:2]:
        style = dict(part.split("=", 1) for part in edge.get("style", "").split(";") if "=" in part)
        endpoints = []
        for terminal, prefix in (("source", "exit"), ("target", "entry")):
            geometry = cells[edge.get(terminal)].find("mxGeometry")
            endpoints.append(
                (
                    float(geometry.get("x")) + float(geometry.get("width")) * float(style[f"{prefix}X"]),
                    float(geometry.get("y")) + float(geometry.get("height")) * float(style[f"{prefix}Y"]),
                )
            )
        effective_endpoints.append(endpoints)

    assert effective_endpoints == [[(198, 82), (198, 140)], [(138, 82), (138, 140)]]
    assert all(not edge.findall("mxGeometry/Array[@as='points']/mxPoint") for edge in edges[:2])
    self_loop_points = edges[2].findall("mxGeometry/Array[@as='points']/mxPoint")
    assert [(float(point.get("x")), float(point.get("y"))) for point in self_loop_points] == [(0, 180), (0, 260), (98, 260)]


def test_drawio_maps_special_class_names_only_through_internal_dot_ids(tmp_path: Path):
    first = 'Box <T> & "quoted"'
    second = "namespace::Thing"
    diagram = UMLDiagram(
        classes={second: UMLClass(second), first: UMLClass(first)},
        relationships=[UMLRelationship(first, second, RelationshipType.ASSOCIATION)],
    )
    output = tmp_path / "diagram.drawio"

    run = render_drawio_with_layout(diagram, output)

    dot_source = run.call_args.kwargs["input"]
    assert first not in dot_source
    assert second not in dot_source
    assert "node_1 -> node_2;" in dot_source
    titles = {cell.get("value") for cell in drawio_cells(output).values() if cell.get("vertex") == "1" and cell.get("parent") == "1"}
    assert titles == {"Box &lt;T&gt; &amp; &quot;quoted&quot;", second}


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("malformed_json", "Graphviz.*JSON"),
        ("missing_node", "Graphviz.*node"),
        ("reversed_bounds", "Graphviz.*bounding box"),
        ("diagonal_route", "Graphviz.*route"),
    ],
)
def test_drawio_rejects_unusable_graphviz_json_geometry(tmp_path: Path, case: str, message: str):
    diagram = UMLDiagram(
        classes={name: UMLClass(name) for name in ("A", "B")},
        relationships=[UMLRelationship("A", "B", RelationshipType.ASSOCIATION)],
    )
    layout: dict[str, object] | str = graphviz_layout_json(diagram)
    if case == "malformed_json":
        layout = "{not JSON"
    elif case == "missing_node":
        layout["objects"] = layout["objects"][:1]
    elif case == "reversed_bounds":
        layout["bb"] = "0,400,400,0"
    else:
        layout["edges"][0]["pos"] = "10,10 20,20"

    with (
        patch("python2uml.renderers.drawio_renderer.get_dot_executable", return_value=BUNDLED_DOT),
        patch("python2uml.renderers.drawio_renderer.subprocess.run", return_value=graphviz_result(layout)),
        pytest.raises(RuntimeError, match=message),
    ):
        DrawioRenderer().render(diagram, str(tmp_path / "diagram.drawio"))
