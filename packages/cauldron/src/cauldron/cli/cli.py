from __future__ import annotations

import string

from pydantic.alias_generators import to_snake
from typer import Typer


def to_dash_case(value: str):
    return to_snake(value).replace("_", "-")


class CLI:
    def __init__(self, name: str, /, *children: CLI, typer: Typer | None = None):
        self._name = name
        self._typer = typer or Typer(
            name=name, no_args_is_help=True, add_help_option=True
        )
        self._children = children
        self._setup_typer()

    @property
    def name(self) -> str:
        return self._name

    @property
    def typer(self) -> Typer:
        return self._typer

    def _setup_typer(self):
        # Setting a callback overrides typer's default behaviour
        # which sets the a single command on the root of the CLI
        # It means the CLI behaves the same with one or several CLI options
        # which this author thinks is more predictable and explicit.
        self._typer.command("hidden", hidden=True)(lambda: None)
        for attr in dir(self):
            obj = getattr(self, attr)
            if (
                attr[0] in string.ascii_letters
                and callable(obj)
                and getattr(obj, "__self__", None) is self
            ):
                self.typer.command(to_dash_case(obj.__name__))(obj)
        for child in self._children:
            self.typer.add_typer(child.typer, name=child.name)
