"""
The entrypoint of the "brewing" binary.

We dynamically build a CLI based on the 'brewing' entrypoint of packages.
"""

import tomllib
from pathlib import Path
import importlib.metadata
from typer import Typer
from brewing.cli import CLI
from brewing.brewing import Brewing


def load_entrypoint(entrypoint: importlib.metadata.EntryPoint) -> CLI | Brewing:
    obj = entrypoint.load()
    error = TypeError(
        f"{obj!r} is not suitable as a brewing entrypoint, it must be a brewing.cli.CLI instance, brewing.Brewing instance, or a callable returning such."
    )
    if isinstance(obj, CLI) or isinstance(obj, Brewing):
        return obj
    if not callable(obj):
        raise error
    obj = obj()
    if isinstance(obj, CLI):
        return obj
    raise error


def find_current_project() -> str | None:
    search_files = [path / "pyproject.toml" for path in Path.cwd().parents]
    project_name: str | None = None
    for file in search_files:
        if file.is_file():
            data = tomllib.loads(file.read_text())
            try:
                project_name = data["project"]["name"]
                break
            except KeyError as error:
                raise ValueError(f"No project.name in {file=}") from error
    return project_name


def cli():
    cli = CLI("brewing", extends=Typer(no_args_is_help=True))
    cli.typer.callback()
    entrypoints = importlib.metadata.entry_points(group="brewing")
    for entrypoint in entrypoints:
        if entrypoint.module.split(".")[0] == find_current_project():
            # The current project, if identifiable, is merged into the
            # top-level typer by providing the name as None
            # Otherwise we will use the entrypoint name to
            cli.typer.add_typer(load_entrypoint(entrypoint).typer, name=None)
        # Regardless of the above, the CLI is always available as a subcommand
        # based on the entrypoint name.
        cli.typer.add_typer(load_entrypoint(entrypoint).typer, name=entrypoint.name)
    return cli


def run():
    cli()()
