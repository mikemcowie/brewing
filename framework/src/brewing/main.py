"""The top level application encapsulating related components."""

from __future__ import annotations

from contextvars import Token
from dataclasses import dataclass, field
from collections.abc import Mapping, Iterable
from typing import Any, Callable
from brewing.cli import CLI, CLIOptions
from brewing.db import DatabaseConnectionConfiguration
from brewing.db.types import DatabaseProtocol
import tomllib
from pathlib import Path
import importlib.metadata
from contextvars import ContextVar
from typing import ClassVar, Protocol


type CLIUnionType = CLI[Any] | Brewing
type EntrypointLoader = Callable[[importlib.metadata.EntryPoint], CLIUnionType]
type CurrentProjectProvider = Callable[[], str | None]


class NoCurrentOptions(LookupError):
    """No settings object has been pushed."""


@dataclass
class BrewingOptions[DBConnT: DatabaseConnectionConfiguration]:
    """Application level settings."""

    name: str
    database: DatabaseProtocol
    current_options: ClassVar[ContextVar[BrewingOptions[Any]]] = ContextVar(
        "current_settings"
    )
    current_options_token: Token[BrewingOptions[Any]] | None = field(
        default=None, init=False
    )

    def __enter__(self):
        self.current_options_token = self.current_options.set(self)
        return self

    def __exit__(self, *_):
        if self.current_options_token:  # pragma: no branch
            self.current_options.reset(self.current_options_token)

    @classmethod
    def current(cls):
        """Return the current settings instance."""
        try:
            return cls.current_options.get()
        except LookupError as error:
            raise NoCurrentOptions(
                "No current options available. "
                "Push settings by constucting a BrewingOptions instance, i.e. "
                "with BrewingOptions(...):"
            ) from error


class BrewingComponentType(Protocol):
    """
    Duck type for any object that can be registered to brewing.

    The register method is called when it is passed to brewing,
    which may be used to connect it to the CLI or any other instantiation.
    """

    def register(self, name: str, brewing: Brewing, /) -> Any:
        """
        Register the component to a brewing instance.

        This functions as a callback to integrate components to brewing.
        """
        ...


class Brewing:
    """The top level application encapsulating related components."""

    def __init__(self, **components: BrewingComponentType):
        self.options = BrewingOptions.current()
        self.cli = CLI(CLIOptions(name=self.options.name))
        self.typer = self.cli.typer
        self.database = self.options.database
        self.components: Mapping[str, BrewingComponentType] = components | {
            "db": self.database
        }
        for name, component in self.components.items():
            component.register(name, self)

    def __getattr__(self, name: str):
        try:
            return self.components[name]
        except KeyError as error:
            raise AttributeError(f"no attribute '{name}' in object {self}.") from error


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
