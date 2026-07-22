"""Project file discovery."""

from __future__ import annotations

from pathlib import Path

from model.enums import ProjectLanguage


class ProjectLoader:
    _extensions_by_language: dict[ProjectLanguage, set[str]] = {
        ProjectLanguage.PYTHON: {".py"},
        ProjectLanguage.JAVA: {".java"},
        ProjectLanguage.CPP: {".cpp", ".cc", ".cxx", ".hpp", ".hh", ".h"},
        ProjectLanguage.C: {".c", ".h"},
    }

    def collect_source_files(self, project_type: ProjectLanguage, *paths: str) -> list[str]:
        allowed_extensions = self._extensions_by_language[project_type]
        filepaths: list[str] = []
        for path in paths:
            candidate = Path(path)
            if candidate.is_dir():
                for file in sorted(candidate.rglob("*")):
                    if file.is_file() and file.suffix.lower() in allowed_extensions:
                        filepaths.append(str(file))
            elif candidate.is_file() and candidate.suffix.lower() in allowed_extensions:
                filepaths.append(str(candidate))
            else:
                raise FileNotFoundError(f"Path {path} does not exist or is not a supported {project_type.value} source file.")
        return sorted(set(filepaths))
