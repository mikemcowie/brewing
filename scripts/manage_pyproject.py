"""Manages certain fields in every pyproject.toml file in the repo"""

from collections.abc import MutableMapping
from functools import cached_property
from pathlib import Path
from typing import Any

import tomlkit
from brewing import CLI
from pygit2.repository import Repository
from typer import Typer


class ProjectManager(CLI):
    def __init__(self, name: str, /, *children: CLI, typer: Typer | None = None):
        self._repo = Repository(__file__)
        self._repo_path = Path(self._repo.path).parent
        super().__init__(name, *children, typer=typer)

    @cached_property
    def all_pyproject(self):
        return tuple(self._repo_path.glob("**/pyproject.toml"))

    def _set_build_system(self, build_system: MutableMapping[str, Any]):
        build_system["requires"] = ["hatchling"]
        build_system["build-backend"] = "hatchling.build"

    def _configure_pyproject(self, path: Path):
        if not path.name == "pyproject.toml":
            raise RuntimeError("Cannot edit non-pyproject.toml file")
        data = tomlkit.loads(path.read_text())
        build_system = data.get("build-system")
        if build_system is not None:
            self._set_build_system(build_system)

    def sync(self):
        [self._configure_pyproject(file) for file in self.all_pyproject]


if __name__ == "__main__":
    ProjectManager("project")()
