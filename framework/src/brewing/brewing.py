"""The top level application encapsulating related components."""

from typing import Any, Callable, Annotated, NamedTuple
from typer import Option
from brewing.cli import CLI, CLIOptions
from brewing.http import BrewingHTTP
from brewing.db import Database
from brewing import settings
import uvicorn


class BrewingCLIOptions(NamedTuple):
    """Configurable options for Brewing's CLI."""

    name: str


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
            reload: Annotated[bool, Option()] = False,
            workers: None | int = None,
            host: str = "0.0.0.0",
            port: int = 8000,
        ):
            uvicorn.run(
                http.app_string_identifier,
                host=host,
                workers=workers,
                port=port,
                reload=reload,
            )

    def init_database(self, component: tuple[str, Database[Any]]):
        """
        Add the database CLI for the application.

        Args:
            component (tuple[str, Database[Any]]): name and database instance.

        """
        name, db = component
        self.cli.typer.add_typer(db.cli.typer, name=name)
