"""Manages certain fields in every pyproject.toml file in the repo"""

# pyright: reportIndexIssue=false
from __future__ import annotations

import shutil
import subprocess
import sys
from enum import StrEnum, auto
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import semver
import structlog
import tomlkit
import yaml
from pygit2.repository import Repository
from typer import Argument

from brewing import CLI, CLIOptions

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from tomlkit.container import Container

logger = structlog.get_logger()


class _VersionBumpType(StrEnum):
    patch = auto()
    minor = auto()
    major = auto()
    prerelease = auto()
    finalize = auto()


class ProjectManager(CLI[CLIOptions]):
    def __init__(self, *args: Any, **kwargs: Any):
        self._repo = Repository(__file__)
        self._repo_path = Path(self._repo.path).parent
        super().__init__(*args, **kwargs)

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
            del data["project"]["dynamic"]
        data["project"]["version"] = str(version)
        urls = data["project"].get("urls")  # type: ignore
        if not urls:
            data["project"]["urls"] = tomlkit.table()
            urls = data["project"]["urls"]  # type: ignore
        urls["Homepage"] = "https://mikemcowie.github.io/brewing/"
        urls["Documentation"] = "https://mikemcowie.github.io/brewing/"
        urls["Repository"] = "https://github.com/mikemcowie/brewing"
        urls["Issues"] = "https://github.com/mikemcowie/brewing"
        urls["Releases"] = "https://github.com/mikemcowie/brewing/releases"

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

    def bump_version(self, bump_type: Annotated[_VersionBumpType, Argument()]):
        version = self._read_version()
        match bump_type:
            case _VersionBumpType.patch:
                version = version.bump_patch()
            case _VersionBumpType.minor:
                version = version.bump_minor()
            case _VersionBumpType.major:
                version = version.bump_major()
            case _VersionBumpType.prerelease:
                version = version.bump_prerelease()
            case _VersionBumpType.finalize:
                version = version.finalize_version()
        [self._configure_pyproject(file, version) for file in self.all_pyproject]

    def sync_pyproject(self):
        version = self._read_version()
        [self._configure_pyproject(file, version) for file in self.all_pyproject]

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
    ProjectManager(CLIOptions("project"))()
