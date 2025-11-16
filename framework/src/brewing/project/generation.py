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
            # Otherwise make a
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
        path = config.path / name
        if not config.path.is_absolute():
            raise MaterializationError(
                "Cannot materialize a file with a relative directory"
            )
        # preflight check that the file does not conflict with any existing files
        # by walking the tree up and checking everything is either a directory or doesn't exist.
        if not config.path.parents:
            raise ValueError("Cannot operate on the root file.")
        dir = (
            config.path.parent
        )  # just assigning dir to prevent possibly unbound variable type error.
        for dir in config.path.parents:
            if dir.is_dir():
                break
            if dir.exists():
                raise MaterializationError(
                    f"cannot materialize {dir=!s} "
                    f"because {dir=!s} exists and is not a directory."
                )
        path.write_text(
            self.content if isinstance(self.content, str) else self.content(config)
        )


@dataclass
class MaterializedFile:
    """Represents a file after its contents and path are computed in the project context."""

    path: Path
    content: str


project = ManagedDirectory(files={}, config=ProjectConfiguration("foo", path=Path()))
print(project)


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
