"""Small helpers shared by the explicit Tree-sitter adapters."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node, Parser

from python2uml.parsers.normalized_ast import SourceDiagnostic


def parse_tree(path: str, language_capsule: object) -> tuple[bytes, Node]:
    source = Path(path).read_bytes()
    return source, Parser(language_capsule).parse(source).root_node


def node_text(source: bytes, node: Node | None) -> str | None:
    return source[node.start_byte : node.end_byte].decode("utf-8") if node is not None else None


def walk_named(node: Node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.named_children))


def tree_diagnostics(path: str, root: Node) -> list[SourceDiagnostic]:
    diagnostics: list[SourceDiagnostic] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            line, column = node.start_point
            message = f"missing {node.type}" if node.is_missing else "unexpected syntax"
            diagnostics.append(SourceDiagnostic(path, line + 1, column + 1, "error", message))
        stack.extend(reversed(node.children))
    return diagnostics
