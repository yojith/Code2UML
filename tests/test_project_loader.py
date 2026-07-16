from pathlib import Path

from model.enums import ProjectLanguage
from parser.project_loader import ProjectLoader


def test_collect_source_files_uses_project_type(tmp_path: Path):
    package = tmp_path / "pkg"
    package.mkdir()
    python_file = tmp_path / "main.py"
    java_file = package / "Main.java"
    python_file.write_text("class A:\n    pass\n", encoding="utf-8")
    java_file.write_text("class Main {}", encoding="utf-8")
    (package / "notes.txt").write_text("ignore", encoding="utf-8")

    loader = ProjectLoader()

    assert loader.collect_source_files(ProjectLanguage.PYTHON, str(tmp_path)) == [str(python_file)]
    assert loader.collect_source_files(ProjectLanguage.JAVA, str(tmp_path)) == [str(java_file)]
