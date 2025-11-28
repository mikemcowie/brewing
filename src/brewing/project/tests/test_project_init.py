"""Project init - start a new brewing project."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import uv
from tenacity import retry, stop_after_delay, wait_exponential_jitter

import brewing
from brewing.cli.testing import BrewingCLIRunner
from brewing.db import testing as db_testing
from brewing.db.settings import DatabaseType
from brewing.project import cli

if TYPE_CHECKING:
    from collections.abc import Callable


@contextmanager
def cd(path: Path | str):
    """Context manager to temporarily change working directory."""
    cwd = Path.cwd()
    os.chdir(str(path))
    yield
    os.chdir(str(cwd))


@contextmanager
def run(*cmd: str, readiness_callback: Callable[..., Any], cwd: Path | None = None):
    """Run given command in a background thread."""
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, cwd=cwd)
    readiness_callback()
    yield
    proc.send_signal(signal.SIGTERM)
    proc.wait(5)
    proc.kill()


def cli_runner():
    runner = BrewingCLIRunner(cli.load())
    return runner


def test_cli_commands_change_if_active_project_found(tmp_path: Path):
    # Given an empty directory
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    with cd(project_dir):
        # list the names of the CLI commands, init is there.
        res = subprocess.run(
            [uv.find_uv_bin(), "run", "brewing", "--help"],
            check=False,
            cwd=project_dir,
            capture_output=True,
            encoding="utf8",
        )
        out = res.stderr + res.stdout
        if res.returncode:
            pytest.fail(out)
        assert "project" in out
        assert "my-project" not in out

        # If I run init in the directory
        runner = cli_runner()
        runner.invoke(
            ["init", "--path", str(project_dir), "--db-type", "sqlite"],
            catch_exceptions=False,
        )
        # Then the command names are different with the existing commands moved
        out = runner.invoke(
            ["init", "--path", str(project_dir), "--db-type", "sqlite"],
            catch_exceptions=False,
        )
        assert "project" in out.output, out.output
        assert "my-project" in out.output, out.output


@pytest.mark.parametrize("db_type", DatabaseType, ids=[t.value for t in DatabaseType])
def test_project_init(tmp_path: Path, db_type: DatabaseType):
    """CLI allows project initialization."""
    # Given an empty directory
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    # If I run init in the directory
    runner = cli_runner()
    runner.invoke(
        ["init", "--path", str(project_dir), "--db-type", db_type.value],
        catch_exceptions=False,
    )
    subprocess.run([uv.find_uv_bin(), "sync"], check=True, cwd=project_dir)
    # Change install of brewing to local install
    subprocess.run(
        [
            uv.find_uv_bin(),
            "add",
            f"{Path(brewing.__file__).parents[2].relative_to(project_dir, walk_up=True)!s}[{db_type.value}]",
        ],
        check=True,
        cwd=project_dir,
    )

    # Then the directory will contain a starter brewing project
    assert {f for f in project_dir.glob("**") if ".venv" not in f.parts} == {
        project_dir,
        project_dir / "README.md",
        project_dir / "pyproject.toml",
        project_dir / "uv.lock",
        project_dir / "src",
        project_dir / "src" / "my_project",
        project_dir / "src" / "my_project" / "__init__.py",
        project_dir / "src" / "my_project" / "app.py",
        project_dir / ".gitignore",
    }

    @retry(wait=wait_exponential_jitter(initial=0.1, max=2), stop=stop_after_delay(10))
    def readiness_callback():
        live_status = httpx.get("http://127.0.0.1:8000/livez")
        live_status.raise_for_status()
        ready_status = httpx.get("http://127.0.0.1:8000/readyz")
        ready_status.raise_for_status()

    # start the dev server (in another thread)
    with (
        db_testing.dev(DatabaseType.postgresql),
        run(
            "uv",
            "run",
            "brewing",
            "http",
            "--dev",
            readiness_callback=readiness_callback,
            cwd=project_dir,
        ),
    ):
        pass  # The test is all in the contextmanager
