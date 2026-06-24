"""AST loading utilities."""

from __future__ import annotations

import ast


class AbstractSyntaxTreeLoader:
    def load(self, *files: str) -> list[ast.AST]:
        tree_list: list[ast.AST] = []
        for filepath in files:
            with open(filepath, "r", encoding="utf-8") as file:
                tree_list.append(ast.parse(file.read()))
        return tree_list
