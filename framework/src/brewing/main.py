"""The top level application encapsulating related components."""

from typing import Any, Callable, Annotated
from typer import Option
from brewing.cli import CLI, CLIOptions
from brewing.http import BrewingHTTP
from brewing.db import Database
from brewing.db import testing
from brewing import settings
import uvicorn
import tomllib
from pathlib import Path
import importlib.metadata


class BrewingHandler:
    """
    Mixin class that registers a handler for a type.

    This triggers code to be executed when an instance of such
    a class is passed when instantiating a brewing instabce.
    """


class Brewing:
    """The top level application encapsulating related components."""

    def __init__(self, name: str, **components: Any):
        self.cli = CLI(CLIOptions(name=name))
        self.typer = self.cli.typer
        self.settings = settings.Settings.current()
        self.components = components | {"db": self.settings.database}
        handlers: dict[type, Callable[[tuple[str, Any]], Any]] = {
            BrewingHTTP: self.init_http_component,
            type(self.settings.database): self.init_database,
        }
        for name, component in self.components.items():
            handlers[type(component)]((name, component))

    def __getattr__(self, name: str):
        try:
            return self.components[name]
        except KeyError as error:
            raise AttributeError(f"no attribute '{name}' in object {self}.") from error

    def init_http_component(self, component: tuple[str, BrewingHTTP]):
        """Initialize an HTTP component into the CLI."""
        name, http = component

        @self.cli.typer.command(name)
        def run(
            dev: Annotated[bool, Option()] = False,
            workers: None | int = None,
            host: str = "0.0.0.0",
            port: int = 8000,
        ):
            """Run the HTTP server."""
            if dev:
                with testing.dev(self.settings.database.database_type):
                    return uvicorn.run(
                        http.app_string_identifier,
                        host=host,
                        port=port,
                        reload=dev,
                    )
            return uvicorn.run(
                http.app_string_identifier,
                host=host,
                workers=workers,
                port=port,
                reload=False,
            )

    def init_database(self, component: tuple[str, Database[Any]]):
        """
        Add the database CLI for the application.

        Args:
            component (tuple[str, Database[Any]]): name and database instance.

        """
        name, db = component
        self.cli.typer.add_typer(db.cli.typer, name=name)


def main_cli(options: CLIOptions | None = None) -> CLI[CLIOptions]:
    """
    Return the main brewing command line.

    This commandline discovers subcommands published
    via [project.entry-points.brewing], includimg brewing's own toolset
    and any other that can be detected in the current context.
    """
    cli = CLI(options or CLIOptions(name="brewing"))
    entrypoints = importlib.metadata.entry_points(group="brewing")
    for entrypoint in entrypoints:
        if entrypoint.module.split(".")[0].replace("_", "-") == current_project():
            # The current project, if identifiable, is merged into the
            # top-level typer by providing the name as None
            # Otherwise we will use the entrypoint name to
            cli.typer.add_typer(load_entrypoint(entrypoint).typer, name=None)
        cli.typer.add_typer(load_entrypoint(entrypoint).typer, name=entrypoint.name)
    return cli


def load_entrypoint(
    entrypoint: importlib.metadata.EntryPoint,
) -> CLI[Any] | Brewing:
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


def current_project() -> str | None:
    """Scan from the current working directory to find the name of the current project."""
    for file in (
        path / "pyproject.toml" for path in [Path.cwd()] + list(Path.cwd().parents)
    ):
        try:
            data = tomllib.loads(file.read_text())
            return data["project"]["name"]
        except KeyError as error:
            raise ValueError(f"No project.name in {file=}") from error
        except FileNotFoundError:
            continue
