"""A content generation toolkit."""

from typing import Callable, MutableMapping, cast
from dataclasses import dataclass, replace
from pathlib import Path

type FileContentGenerator = str | Callable[[ProjectConfiguration], str]
type FileNameGenerator = str | Callable[[ProjectConfiguration], str]
type Directory = MutableMapping[FileNameGenerator, File]
type File = FileContentGenerator | str | Directory


@dataclass
class ProjectConfiguration:
    """Shared context for the project initialization."""

    name: str
    path: Path


@dataclass
class ManagedDirectory:
    """A directory whose contents are managed by brewing."""

    files: Directory
    config: ProjectConfiguration


class MaterializationError(RuntimeError):
    """Error raised while materializing a file."""


def materialize_directory(directory: ManagedDirectory) -> None:
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
            materialize_file(file, filename, directory.config)
            continue
        path.mkdir(exist_ok=True, parents=True)
        subdir = directory.__class__(
            files=cast(Directory, directory.files[name_generator]),
            config=replace(directory.config, path=path),
        )
        materialize_directory(subdir)


def materialize_file(content: str, filename: str, config: ProjectConfiguration) -> None:
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
    (config.path / filename).write_text(content)
