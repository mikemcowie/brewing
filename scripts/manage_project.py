"""Manages certain fields in every pyproject.toml file in the repo"""

import shutil
import subprocess
import sys
from collections.abc import MutableMapping
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any

import semver
import structlog
import tomlkit
import yaml
from brewing import CLI
from pygit2.repository import Repository
from tomlkit.container import Container
from typer import Option, Typer

logger = structlog.get_logger()


class ProjectManager(CLI):
    def __init__(self, name: str, /, *children: CLI, typer: Typer | None = None):
        self._repo = Repository(__file__)
        self._repo_path = Path(self._repo.path).parent
        super().__init__(name, *children, typer=typer)

    @cached_property
    def all_pyproject(self):
        return (
            self._repo_path / "pyproject.toml",
            *self._repo_path.glob("**/pyproject.toml"),
        )

    def _clean_dist_dir(self) -> Path:
        dist_dir = self._repo_path / "dist"
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir()
        return dist_dir

    def _run(self, *cmd: str) -> str:
        """Run command in subprocess; return stdout as a string."""
        logger.info(f"running {cmd=}")
        try:
            return subprocess.run(
                cmd, capture_output=True, encoding="utf8", check=True
            ).stdout
        except subprocess.CalledProcessError as error:
            logger.error(str(error.stdout + str(error.stderr)))  # noqa: TRY400
            sys.exit(1)

    def _published_packages(self) -> list[Path]:
        return [
            path.parent
            for path in self.all_pyproject
            if path.parent == self._repo_path / "framework"
            or path.parent.parent == self._repo_path / "libs"
        ]

    def _set_build_system(self, data: MutableMapping[str, Any]):
        data["build-system"]["requires"] = ["hatchling"]
        data["build-system"]["build-backend"] = "hatchling.build"

    def _set_project_table(self, data: Container, version: semver.Version):
        if data["project"].get("dynamic"):  # type: ignore
            del data["project"]["dynamic"]  # type: ignore
        data["project"]["version"] = str(version)  # type: ignore

    def _read_version(self) -> semver.Version:
        project_file = self._repo_path / "pyproject.toml"
        file_contents = project_file.read_text()
        data = tomlkit.loads(file_contents)
        version: str = data["project"]["version"]  # type: ignore
        return semver.Version.parse(version)

    def _configure_pyproject(self, path: Path, version: semver.Version):
        if not path.name == "pyproject.toml":
            raise RuntimeError("Cannot edit non-pyproject.toml file")
        data = tomlkit.loads(path.read_text())
        build_system = data.get("build-system")  # type: ignore
        if build_system:
            self._set_build_system(data)
        self._set_project_table(data, version)
        logger.info(f"writing {version=} to {path=}")
        path.write_text(tomlkit.dumps(data))  # type: ignore

    def sync_pyproject(
        self, version: Annotated[str, Option(default=..., envvar="SET_VERSION")]
    ):
        [
            self._configure_pyproject(file, semver.Version.parse(version))
            for file in self.all_pyproject
        ]

    def sync_dependabot(self):
        dependabot_config: dict[str, Any] = {
            "version": 2,
            "updates": [
                {
                    "package-ecosystem": "uv",
                    "directory": "/",
                    "schedule": {"interval": "weekly"},
                },
                *[
                    {
                        "package-ecosystem": "pip",
                        "directory": str(path.parent.relative_to(self._repo_path)),
                        "schedule": {"interval": "weekly"},
                    }
                    for path in self.all_pyproject
                ],
            ],
        }
        (self._repo_path / ".github" / "dependabot.yml").write_text(
            yaml.safe_dump(dependabot_config)
        )

    def release(self):
        version = self._read_version()
        dist_dir = self._clean_dist_dir()
        for project in self._published_packages():
            self._run("uv", "build", str(project), "--out-dir", str(dist_dir))
        release_cmd = [
            "gh",
            "release",
            "create",
            str(version),
            "--generate-notes",
            "--title",
            str(self._read_version()),
        ]

        upload_cmd = [
            "gh",
            "release",
            "upload",
            str(version),
            *(
                str(asset)
                for asset in dist_dir.iterdir()
                if asset.suffix in (".whl", ".gz")
            ),
        ]
        if version.prerelease or version.build:
            release_cmd.append("--prerelease")

        self._run(*release_cmd)
        self._run(*upload_cmd)

    def publish(self):
        version = self._read_version()
        dist_dir = self._clean_dist_dir()
        self._run("gh", "release", "download", str(version), "--dir", str(dist_dir))
        self._run(
            "uv",
            "publish",
            f"{dist_dir!s}/*",
            "--trusted-publishing",
            "always",
        )


if __name__ == "__main__":
    ProjectManager("project")()
