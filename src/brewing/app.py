"""The top level application encapsulating related components."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Protocol

from brewing.cli import CLI, CLIOptions
from brewing.context import push_app
from brewing.serialization import ExcludeCachedProperty

if TYPE_CHECKING:
    from brewing.db import Database

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
class Brewing(ExcludeCachedProperty):
    """The top level application encapsulating related components."""

    name: str
    database: Database
    components: dict[str, BrewingComponentType | Database]
    current_component: BrewingComponentType | None = None

    def __post_init__(self):
        for name, component in self.all_components.items():
            component.register(name, self)

    @cached_property
    def cli(self):
        return CLI(CLIOptions(name=self.name))

    @cached_property
    def typer(self):
        return self.cli.typer

    @cached_property
    def all_components(self):
        return self.components | {"db": self.database}

    def __getstate__(self) -> dict[str, Any]:
        state = super().__getstate__()
        state.pop("_push", None)
        return state

    def __enter__(self):
        self._push = push_app(self)
        self._push.__enter__()

    def __exit__(self, *args: Any):
        self._push.__exit__(*args)
