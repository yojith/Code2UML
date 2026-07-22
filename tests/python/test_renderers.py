from pathlib import Path
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
from python2uml.renderers.graphviz_renderer import GraphvizRenderer


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


def test_graphviz_render_fails_when_dot_is_missing():
    with patch("python2uml.renderers.graphviz_renderer.shutil.which", return_value=None), pytest.raises(RuntimeError, match="Install Graphviz"):
        GraphvizRenderer().render(UMLDiagram(), "out.svg")


def test_graphviz_source_maps_every_class_kind_and_relationship_style():
    renderer = GraphvizRenderer()
    dot = renderer.create_dot()

    with patch.object(renderer, "create_dot", return_value=dot), patch.object(renderer, "_ensure_dot_available"), patch.object(dot, "render"):
        renderer.render(diagram_with_every_style(), "out.svg")

    for kind in ClassKind:
        expected_title = kind.value if kind == ClassKind.CLASS else f"&lt;&lt;{kind.value}&gt;&gt; {kind.value}"
        assert expected_title in dot.source
    for expected in (
        "arrowhead=onormal",
        "arrowhead=onormal style=dashed",
        "arrowhead=normal",
        "arrowtail=odiamond dir=back",
        "arrowtail=diamond dir=back",
    ):
        assert expected in dot.source


def test_drawio_xml_maps_every_class_kind_and_relationship_style(tmp_path: Path):
    output = tmp_path / "diagram.drawio"

    DrawioRenderer().render(diagram_with_every_style(), str(output))

    cells = ET.parse(output).getroot().findall(".//mxCell")
    labels = {cell.get("value") for cell in cells if cell.get("vertex") == "1"}
    styles = {cell.get("style") for cell in cells if cell.get("edge") == "1"}
    assert labels == {kind.value if kind == ClassKind.CLASS else f"<<{kind.value}>> {kind.value}" for kind in ClassKind}
    assert styles == {
        "endArrow=block;endFill=0;",
        "endArrow=block;endFill=0;dashed=1;",
        "endArrow=open;",
        "startArrow=diamond;startFill=0;endArrow=none;",
        "startArrow=diamond;startFill=1;endArrow=none;",
    }


def test_graphviz_source_escapes_dynamic_html_label_text():
    renderer = GraphvizRenderer()
    dot = renderer.create_dot()
    uml_class = UMLClass(
        "Box<T>&",
        kind=ClassKind.INTERFACE,
        attributes=[UMLAttribute("items<&>", "List<Order>&")],
        methods=[UMLMethod("find<&>", ["key: Map<K, V>&"], "Result<T>&")],
    )

    with patch.object(renderer, "create_dot", return_value=dot), patch.object(renderer, "_ensure_dot_available"), patch.object(dot, "render"):
        renderer.render(UMLDiagram(classes={uml_class.name: uml_class}), "out.svg")

    assert "&lt;&lt;interface&gt;&gt; Box&lt;T&gt;&amp;" in dot.source
    assert "items&lt;&amp;&gt;: List&lt;Order&gt;&amp;" in dot.source
    assert "find&lt;&amp;&gt;(key: Map&lt;K, V&gt;&amp;): Result&lt;T&gt;&amp;" in dot.source


def test_drawio_xml_preserves_attribute_and_return_types(tmp_path: Path):
    output = tmp_path / "diagram.drawio"
    uml_class = UMLClass(
        "Repository",
        attributes=[UMLAttribute("items", "List<Order>")],
        methods=[UMLMethod("find", ["id: int"], "Order")],
    )

    DrawioRenderer().render(UMLDiagram(classes={uml_class.name: uml_class}), str(output))

    label = ET.parse(output).getroot().find(".//mxCell[@vertex='1']").get("value")
    assert "+ items: List<Order>" in label
    assert "+ find(id: int): Order" in label
