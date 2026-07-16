from unittest.mock import patch

import pytest

from model.uml_diagram import UMLDiagram
from render.graphviz_renderer import GraphvizRenderer


def test_graphviz_render_fails_when_dot_is_missing():
    with patch("render.graphviz_renderer.shutil.which", return_value=None), pytest.raises(RuntimeError, match="Install Graphviz"):
        GraphvizRenderer().render(UMLDiagram(), "out.svg")
