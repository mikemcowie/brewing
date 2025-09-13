from __future__ import annotations

import string
from typing import Any

from pydantic.alias_generators import to_snake
from typer import Typer


def to_dash_case(value: str):
    return to_snake(value).replace("_", "-")


class ConflictingCommandError(ValueError):
    pass


class CLI:
    """A class-based command-line generator based on typer."""

    _self = object()  # sentinal value to serve as default for wraps

    def __init__(
        self,
        name: str,
        /,
        *children: CLI,
        extends: Typer | CLI | None = None,
        wraps: Any = _self,
    ):
        """_summary_

        Args:
            name (str): The name of the CLI - this will be used in nested situations
            typer (Typer  | CLI | None, optional): If provided, a typer instance or another CLI to add commands to.
            wraps (Any): Object to obtain CLI commands from. If not provided, self will be used.
        """
        self._name = name
        if isinstance(extends, Typer):
            self._typer = extends
        elif isinstance(extends, CLI):
            self._typer = extends.typer
        else:
            self._typer = Typer(name=name, no_args_is_help=True, add_help_option=True)
        self._children = children
        self._wraps = self if wraps is self._self else wraps
        self._setup_typer()

    @property
    def name(self) -> str:
        """Read only name attribute.

        Returns:
            str: The name of the CLI as provided at instantiation.
        """
        return self._name

    @property
    def command_names(self):
        return tuple(command.name for command in self.typer.registered_commands)

    @property
    def typer(self) -> Typer:
        """Read only name attribute.

        Returns:
            Typer: the typer instance that the class wraps around, as generated or provided at instantiation.
        """
        return self._typer

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Runs the CLI."""
        return self.typer(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self.typer, name)

    def _setup_typer(self):
        # Setting a callback overrides typer's default behaviour
        # which sets the a single command on the root of the CLI
        # It means the CLI behaves the same with one or several CLI options
        # which this author thinks is more predictable and explicit.
        self._typer.command("hidden", hidden=True)(lambda: None)
        for attr in dir(self._wraps):
            obj = getattr(self._wraps, attr)
            if (
                attr[0] in string.ascii_letters
                and callable(obj)
                and getattr(obj, "__self__", None) is self._wraps
            ):
                command_name = to_dash_case(obj.__name__)
                if command_name in self.command_names:
                    raise ConflictingCommandError(
                        f"cannot add CLI command with conflicting {command_name=}."
                    )
                self.typer.command(command_name)(obj)
        for child in self._children:
            self.typer.add_typer(child.typer, name=child.name)
