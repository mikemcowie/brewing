from __future__ import annotations

import string
from typing import Any

from pydantic.alias_generators import to_snake
from typer import Typer


def to_dash_case(value: str):
    return to_snake(value).replace("_", "-")


class CLI:
    """A class-based command-line generator based on typer.

    !!! note

        The main goal of this functionality is to make it easier to build embedded command lines, so that for example
        you can provide a command line as part of a library, and make it easy for consumers to embed the command line
        into their own wider CLI application.

        If you just want a simple CLI in the global scope of a python module, this package offers nothing compared to typer.

    brewing's CLI class is an object-oriented wrapper around Tiangolo's [Typer](https://typer.tiangolo.com/), which itself
    builds on PalletsProjects' [click](https://click.palletsprojects.com/en/stable/).


    To write a CLI, simply inherit from brewing.cli.CLI, write a python class with type hints on the methods,
    and instantiate an instance of that class. brewing CLI will automatically build a CLI based on the public methods of the class.



    ```python
    from brewing import CLI


    class MyCLI(CLI):
        def greet(self, message: str):
            print("message")


    cli = MyCLI("mycli").typer
    ```


    typer is transparently used to parse the methods, so all of its documentation about how to declare arguments and options is applicable.
    To explicitely declare a parameter to be an option, use typing.Annotated with typer's Option class.


    ```python
    from typing import Annotated
    from typer import Option
    from brewing import CLI


    class MyCLI(CLI):
        def greet(self, message: [Annotated[str, Option()]]):
            print("message")
    ```
    """

    def __init__(self, name: str, /, *children: CLI, typer: Typer | None = None):
        """_summary_

        Args:
            name (str): The name of the CLI - this will be used in nested situations
            typer (Typer | None, optional): If provided, a pre-exisitng Typer instance to extend.
        """
        self._name = name
        self._typer = typer or Typer(
            name=name, no_args_is_help=True, add_help_option=True
        )
        self._children = children
        self._setup_typer()

    @property
    def name(self) -> str:
        """Read only name attribute.

        Returns:
            str: The name of the CLI as provided at instantiation.
        """
        return self._name

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
