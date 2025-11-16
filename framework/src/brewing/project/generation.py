"""A content generation toolkit."""

from typing import Callable, MutableMapping
from dataclasses import dataclass, replace
from pathlib import Path
from brewing.project.state import ProjectConfiguration


type FileContentGenerator = str | Callable[[ProjectConfiguration], str]
type FileNameGenerator = str | Callable[[ProjectConfiguration], str]
type Directory = MutableMapping[str, File]
type File = NormalFile | Directory


@dataclass
class ManagedDirectory:
    """A directory whose contents are managed by brewing."""

    files: Directory
    config: ProjectConfiguration

    @property
    def root(self) -> Path:
        """The root directory of the project."""
        return self.config.path

    def materialize(self) -> None:
        """Ensure that the directory matches the configuration."""
        for name, file in self.files.items():
            path = self.root / name
            if isinstance(file, NormalFile):
                file.materialize_with(name, self.config)
                continue
            # Otherwise make a directory and repeat
            # on that directory.
            path.mkdir(exist_ok=True, parents=True)
            subdir = self.__class__(files=file, config=replace(self.config, path=path))
            subdir.materialize()


class MaterializationError(RuntimeError):
    """Error raised while materializing a file."""


@dataclass
class NormalFile:
    """Represents a file to be generated."""

    content: str | FileContentGenerator

    def materialize_with(self, name: str, config: ProjectConfiguration) -> None:
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
        (config.path / name).write_text(
            self.content if isinstance(self.content, str) else self.content(config)
        )


def test_project_materializes_files_in_immediate_directory(tmp_path: Path):
    """Simplest test: 2 files in immediate directory."""
    # Given we setup test-project in an empty directory
    files: Directory = {
        "file1": NormalFile(content="foo"),
        "file2": NormalFile(content="bar"),
    }
    project = ManagedDirectory(
        files=files, config=ProjectConfiguration(name="test-project", path=tmp_path)
    )
    assert not list(tmp_path.iterdir())
    # If we materialize the project.
    project.materialize()
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
        "some-file0": NormalFile(content="some-file0-content"),
        "dir1": {
            "some-file1": NormalFile(content="some-file1-content"),
            "dir2": {
                "some-file2": NormalFile(content="some-file2-content"),
                "dir3": {
                    "some-file3": NormalFile(content="some-file3-content"),
                },
            },
        },
    }
    project = ManagedDirectory(
        files=files, config=ProjectConfiguration(name="test", path=tmp_path)
    )
    # If we materialize
    project.materialize()
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
