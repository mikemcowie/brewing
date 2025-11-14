"""
Brewing plugin mechanism.

Brewing permits to register package entrypoints, being objects that
provide a CLI that can be attached to the brewing CLI.

This module has functionality to load these plugins.
"""

from collections.abc import Iterable
from pathlib import Path
import tomllib
from typing import Callable
from brewing.cli import CLI, CLIOptions
from brewing.app import Brewing, CLIUnionType


import importlib.metadata

type EntrypointLoader = Callable[[importlib.metadata.EntryPoint], CLIUnionType]
type CurrentProjectProvider = Callable[[], str | None]


def load_entrypoint(
    entrypoint: importlib.metadata.EntryPoint,
) -> CLIUnionType:
    """Process/filter packaging entrypoints to the CLI."""
    obj = entrypoint.load()
    error = TypeError(
        f"{obj!r} is not suitable as a brewing entrypoint, it must be a brewing.cli.CLI instance, brewing.Brewing instance, or a callable returning such."
    )
    if isinstance(obj, CLI) or isinstance(obj, Brewing):
        return obj  # pyright: ignore[reportUnknownVariableType]
    if not callable(obj):
        raise error
    obj = obj()
    if isinstance(obj, CLI):
        return obj  # pyright: ignore[reportUnknownVariableType]
    raise error


def current_project(search_dir: Path | None = None) -> str | None:
    """Scan from the current working directory to find the name of the current project."""
    search_dir = search_dir or Path.cwd()
    for file in (
        path / "pyproject.toml" for path in [search_dir] + list(search_dir.parents)
    ):
        try:
            data = tomllib.loads(file.read_text())
            return data["project"]["name"]
        except KeyError as error:
            raise ValueError(f"No project.name in {file=!s}") from error
        except FileNotFoundError:
            continue


def main_cli(
    options: CLIOptions | None = None,
    entrypoints: Iterable[importlib.metadata.EntryPoint] | None = None,
    entrypoint_loader: EntrypointLoader = load_entrypoint,
    project_provider: CurrentProjectProvider = current_project,
) -> CLI[CLIOptions]:
    """
    Return the main brewing command line.

    This commandline discovers subcommands published
    via [project.entry-points.brewing], includimg brewing's own toolset
    and any other that can be detected in the current context.
    """
    cli = CLI(options or CLIOptions(name="brewing"))
    entrypoints = [
        e
        for e in (entrypoints or importlib.metadata.entry_points())
        if e.group == "brewing"
    ]
    for entrypoint in entrypoints:
        if entrypoint.module.split(".")[0].replace("_", "-") == project_provider():
            # The current project, if identifiable, is merged into the
            # top-level typer by providing the name as None
            # Otherwise we will use the entrypoint name to
            cli.typer.add_typer(entrypoint_loader(entrypoint).typer, name=None)
        cli.typer.add_typer(entrypoint_loader(entrypoint).typer, name=entrypoint.name)
    return cli
