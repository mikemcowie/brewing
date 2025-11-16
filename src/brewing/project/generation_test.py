"""Unit tests for for generation.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from brewing.project.generation import (
    Directory,
    ManagedDirectory,
    materialize_directory,
)
from brewing.project.state import ProjectConfiguration

if TYPE_CHECKING:
    from pathlib import Path


def test_project_materializes_files_in_immediate_directory(tmp_path: Path):
    """Simplest test: 2 files in immediate directory."""
    # Given we setup test-project in an empty directory
    files: Directory = {
        "file1": "foo",
        "file2": "bar",
    }
    directory = ManagedDirectory(
        files=files, config=ProjectConfiguration(name="test-project", path=tmp_path)
    )
    assert not list(tmp_path.iterdir())
    # If we materialize the project.
    materialize_directory(directory)
    # Then the expected files are  in place
    assert sorted(tmp_path.iterdir()) == sorted(
        [tmp_path / "file1", tmp_path / "file2"]
    )
    # And have the expected content
    assert (tmp_path / "file1").read_text() == "foo"
    assert (tmp_path / "file2").read_text() == "bar"


def test_project_materializes_subdirectories(tmp_path: Path):
    """We can use nested dicts to describe a target state with subdirectories and materialize it."""
    # Given a target state of several layers of files and directories.
    files: Directory = {
        "empty-dir": {},
        "some-file0": "some-file0-content",
        "dir1": {
            "some-file1": "some-file1-content",
            "dir2": {
                "some-file2": "some-file2-content",
                "dir3": {
                    "some-file3": "some-file3-content",
                },
            },
        },
    }
    directory = ManagedDirectory(
        files=files, config=ProjectConfiguration(name="test", path=tmp_path)
    )
    # If we materialize
    materialize_directory(directory)
    # Then we can check the filesystem matches what was expected.
    assert set(tmp_path.glob("**")) == {
        tmp_path,
        tmp_path / "empty-dir",
        tmp_path / "some-file0",
        tmp_path / "dir1",
        tmp_path / "dir1" / "some-file1",
        tmp_path / "dir1" / "dir2",
        tmp_path / "dir1" / "dir2" / "some-file2",
        tmp_path / "dir1" / "dir2" / "dir3",
        tmp_path / "dir1" / "dir2" / "dir3" / "some-file3",
    }
    # And we can check the relevent files are files versus directories
    for file in tmp_path.glob("**"):
        if "dir" in file.name:
            assert file.is_dir()
        elif "file" in file.name:
            assert file.is_file()
    # And check the file content
    assert (tmp_path / "some-file0").read_text() == "some-file0-content"
    assert (tmp_path / "dir1" / "some-file1").read_text() == "some-file1-content"
    assert (
        tmp_path / "dir1" / "dir2" / "some-file2"
    ).read_text() == "some-file2-content"
    assert (
        tmp_path / "dir1" / "dir2" / "dir3" / "some-file3"
    ).read_text() == "some-file3-content"


def test_computing(tmp_path: Path):
    """We can use callables intead of literals both to define file names and file content."""

    # Given a target state of several layers of files and directories
    # with all of them being callables
    def _get_dir_name(config: ProjectConfiguration):
        return config.name

    def _get_file_name(config: ProjectConfiguration):
        return f"{config.name}-file"

    def _get_file_content(config: ProjectConfiguration):
        return f"{config.name}-file-content"

    files: Directory = {
        _get_dir_name: {_get_file_name: _get_file_content},
    }

    directory = ManagedDirectory(
        files=files, config=ProjectConfiguration(name="test-computed", path=tmp_path)
    )
    materialize_directory(directory)
    assert set(tmp_path.glob("**")) == {
        tmp_path,
        tmp_path / "test-computed",
        tmp_path / "test-computed" / "test-computed-file",
    }
    assert (
        tmp_path / "test-computed" / "test-computed-file"
    ).read_text() == "test-computed-file-content"
