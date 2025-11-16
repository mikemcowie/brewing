"""A content generation toolkit."""

from typing import Callable, MutableMapping, cast
from dataclasses import dataclass, replace
from pathlib import Path
from brewing.project.state import ProjectConfiguration


type FileContentGenerator = str | Callable[[ProjectConfiguration], str]
type FileNameGenerator = str | Callable[[ProjectConfiguration], str]
type Directory = MutableMapping[FileNameGenerator, File]
type File = FileContentGenerator | str | Directory


@dataclass
class ManagedDirectory:
    """A directory whose contents are managed by brewing."""

    files: Directory
    config: ProjectConfiguration


class MaterializationError(RuntimeError):
    """Error raised while materializing a file."""


def materialize_directory_tree(directory: ManagedDirectory) -> None:
    """Ensure that the directory matches the configuration."""
    for name_generator, file_generator in list(directory.files.items()):
        filename = (
            name_generator(directory.config)
            if callable(name_generator)
            else name_generator
        )
        file = (
            file_generator(directory.config)
            if callable(file_generator)
            else file_generator
        )
        path = directory.config.path / filename
        if isinstance(file, str):
            materialize_contnet(file, filename, directory.config)
            continue
        path.mkdir(exist_ok=True, parents=True)
        subdir = directory.__class__(
            files=cast(Directory, directory.files[name_generator]),
            config=replace(directory.config, path=path),
        )
        materialize_directory_tree(subdir)


def materialize_contnet(content: str, name: str, config: ProjectConfiguration) -> None:
    """Materializes the file within the given directory."""
    if not config.path.is_absolute():
        raise MaterializationError(
            "Cannot materialize a file with a relative directory"
        )
    # preflight check that the file does not conflict with any existing files
    # by walking the tree up and checking everything is either a directory or doesn't exist.
    if not config.path.parents:
        raise ValueError("Cannot operate on the root file.")
    config.path.mkdir(exist_ok=True, parents=True)
    (config.path / name).write_text(content)


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
    materialize_directory_tree(directory)
    # Then the expected files are  in place
    assert sorted(list(tmp_path.iterdir())) == sorted(
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
    materialize_directory_tree(directory)
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
    materialize_directory_tree(directory)
    assert set(tmp_path.glob("**")) == {
        tmp_path,
        tmp_path / "test-computed",
        tmp_path / "test-computed" / "test-computed-file",
    }
    assert (
        tmp_path / "test-computed" / "test-computed-file"
    ).read_text() == "test-computed-file-content"
