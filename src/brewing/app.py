"""The top level application encapsulating related components."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Protocol

from brewing.cli import CLI, CLIOptions
from brewing.context import push_app

if TYPE_CHECKING:
    from brewing.db.types import DatabaseProtocol

type CLIUnionType = CLI[Any] | Brewing


class NoCurrentOptions(LookupError):
    """No settings object has been pushed."""


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


@dataclass
class Brewing:
    """The top level application encapsulating related components."""

    name: str
    database: DatabaseProtocol
    components: dict[str, BrewingComponentType | DatabaseProtocol]

    @cached_property
    def cli(self):
        return CLI(CLIOptions(name=self.name))

    @property
    def typer(self):
        return self.cli.typer

    @cached_property
    def all_components(self):
        return self.components | {"db": self.database}

    def __enter__(self):
        for name, component in self.all_components.items():
            component.register(name, self)
        self._push = push_app(self)
        self._push.__enter__()

    def __exit__(self, *args: Any):
        self._push.__exit__(*args)
