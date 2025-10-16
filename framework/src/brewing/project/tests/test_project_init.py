"""Project init - start a new brewing project."""

import sys
import signal
import uv
import subprocess
from typing import Callable, Any
from contextlib import contextmanager
import httpx
from pathlib import Path
import brewing
from brewing.cli.testing import BrewingCLIRunner
from brewing.cli import global_cli
from brewing.project import cli
from fastapi import status
from tenacity import retry, wait_exponential_jitter, stop_after_delay


@contextmanager
def run(*cmd: str, readiness_callback: Callable[..., Any]):
    """Run given command in a background thread."""
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
    readiness_callback()
    yield
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=5)


def cli_runner():
    runner = BrewingCLIRunner(cli.load())
    return runner


def test_cli_commands_change_if_active_project_found(tmp_path: Path):
    # Given an empty directory
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    # list the names of the CLI commands, init is there.
    no_project_commands = global_cli.cli().command_names
    assert "init" in no_project_commands
    assert "db" not in no_project_commands

    # If I run init in the directory
    runner = cli_runner()
    runner.invoke(["init", "--path", str(project_dir)], catch_exceptions=False)
    # Then the command names are different with the existing commands moved
    active_project_commands = global_cli.cli().command_names
    assert "init" not in active_project_commands
    assert "db" in active_project_commands


def test_project_init(tmp_path: Path):
    """CLI allows project initialization."""
    # Given an empty directory
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    # If I run init in the directory
    runner = cli_runner()
    runner.invoke(["init", "--path", str(project_dir)], catch_exceptions=False)
    subprocess.run([uv.find_uv_bin(), "sync"], check=True, cwd=project_dir)
    # Change install of brewing to local install
    subprocess.run(
        [
            uv.find_uv_bin(),
            "add",
            str(
                Path(brewing.__file__).parents[2].relative_to(project_dir, walk_up=True)
            ),
        ],
        check=True,
        cwd=project_dir,
    )

    # Then the directory will contain a starter brewing project
    assert set(f for f in project_dir.glob("**") if ".venv" not in f.parts) == {
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
    with run("uv", "run", "brewing", "dev", readiness_callback=readiness_callback):
        result = httpx.get("http://127.0.0.1:8000")
        assert result.status_code == status.HTTP_200_OK
        assert "It works!!" in result.text
