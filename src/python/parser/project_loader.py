"""Project file discovery."""

from __future__ import annotations

from pathlib import Path


class ProjectLoader:
    def collect_python_files(self, *paths: str) -> list[str]:
        filepaths: list[str] = []
        for path in paths:
            candidate = Path(path)
            if candidate.is_dir():
                filepaths.extend(str(file) for file in candidate.rglob("*.py"))
            elif candidate.is_file() and candidate.suffix == ".py":
                filepaths.append(str(candidate))
            else:
                raise FileNotFoundError(f"Path {path} does not exist.")
        return filepaths
