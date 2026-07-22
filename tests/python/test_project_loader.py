from pathlib import Path

import pytest

from python2uml.model.enums import ProjectLanguage
from python2uml.parsers.project_loader import ProjectLoader


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


def test_collect_source_files_is_recursive_and_deterministic(tmp_path: Path):
    nested = tmp_path / "z" / "nested"
    nested.mkdir(parents=True)
    first = tmp_path / "a.py"
    second = nested / "b.py"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")

    assert ProjectLoader().collect_source_files(ProjectLanguage.PYTHON, str(nested), str(first)) == [str(first), str(second)]


def test_collect_source_files_shares_headers_between_c_and_cpp(tmp_path: Path):
    header = tmp_path / "model.h"
    c_source = tmp_path / "model.c"
    cpp_source = tmp_path / "model.cpp"
    for source in (header, c_source, cpp_source):
        source.write_text("", encoding="utf-8")

    loader = ProjectLoader()

    assert loader.collect_source_files(ProjectLanguage.C, str(tmp_path)) == [str(c_source), str(header)]
    assert loader.collect_source_files(ProjectLanguage.CPP, str(tmp_path)) == [str(cpp_source), str(header)]


def test_collect_source_files_deduplicates_overlapping_inputs(tmp_path: Path):
    source = tmp_path / "model.py"
    source.write_text("", encoding="utf-8")

    assert ProjectLoader().collect_source_files(ProjectLanguage.PYTHON, str(tmp_path), str(source)) == [str(source)]


@pytest.mark.parametrize("name", ["notes.txt", "missing.py"])
def test_collect_source_files_rejects_unsupported_and_missing_paths(tmp_path: Path, name: str):
    path = tmp_path / name
    if name == "notes.txt":
        path.write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="does not exist or is not a supported python source file"):
        ProjectLoader().collect_source_files(ProjectLanguage.PYTHON, str(path))
