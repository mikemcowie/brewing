"""The top level application encapsulating related components."""

from __future__ import annotations

from contextvars import Token
from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any
from brewing.cli import CLI, CLIOptions
from brewing.db import DatabaseConnectionConfiguration
from brewing.db.types import DatabaseProtocol
from contextvars import ContextVar
from typing import ClassVar, Protocol


type CLIUnionType = CLI[Any] | Brewing


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
