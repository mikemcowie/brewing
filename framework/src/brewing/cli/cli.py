"""Implementation of the core CLI class."""

from __future__ import annotations

import inspect
import string
from collections.abc import Callable
from typing import (
    Annotated,
    Any,
    get_type_hints,
    TYPE_CHECKING,
    Protocol,
    NamedTuple,
)

from pydantic.alias_generators import to_snake
from typer import Option, Typer
from typer.models import ArgumentInfo, OptionInfo


def _to_dash_case(value: str):
    return to_snake(value).replace("_", "-")


class ConflictingCommandError(ValueError):
    """A conflict was found setting up the CLI."""


type Revisable = Callable[..., Any]

_CALLBACK_KEY = "_callback"


def _callback(*args: Any, **kwargs: Any):
    """Mark give function to be intepreted as a typer callback."""

    def _inner[T: Callable[..., Any]](func: T) -> T:
        setattr(func, _CALLBACK_KEY, dict(args=args, kwargs=kwargs))
        return func

    return _inner


if TYPE_CHECKING:
    callback = Typer().callback
else:
    callback = _callback


def _is_callback(func: Any) -> bool:
    """Return whether given function or object should be intepreted as a typer callback."""
    return hasattr(func, _CALLBACK_KEY)


def _revise_annotation(func: Revisable, param: inspect.Parameter) -> Any:
    """Return a revised annotation for parameter of function."""
    type_hint = get_type_hints(func, include_extras=True).get(
        param.name
    )  # Needed for the values of annotations
    if type_hint is None:
        return None
    metadata = getattr(type_hint, "__metadata__", ())
    if metadata and [
        item for item in metadata if isinstance(item, OptionInfo | ArgumentInfo)
    ]:
        # The item is already annotated with typer annotions, return it unchanged
        return param.annotation

    if param.kind in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL):
        raise TypeError("Cannot support positional-only arguments.")
    else:
        typer_param_type = Option
    return Annotated[param.annotation, *((*metadata, typer_param_type()))]


def _revise_annotations(func: Revisable):
    func.__annotations__ = {
        name: _revise_annotation(func, param)
        for name, param in inspect.signature(func, eval_str=True).parameters.items()
    }


class CLIBaseOptions(Protocol):
    """Base duck-type class for CLI options."""

    @property
    def name(self) -> str:
        """The name of the CLI, to be used as a default in nested situations."""
        ...


class CLIOptions(NamedTuple):
    """Minimal configuration options for a CLI."""

    name: str


class CLI[OptionsT: CLIBaseOptions]:
    """A class-based command-line generator based on typer."""

    _self = object()  # sentinal value to serve as default for wraps

    def __init__(
        self,
        options: OptionsT,
        /,
        *children: CLI[Any],
        help: str | None = None,
        extends: Typer | CLI[Any] | None = None,
        wraps: Any = _self,
    ):
        """
        Initialize the CLI.

        Args:
            options (OptionsT): Options for this CLI.
            *children: CLI: Additional  CLIs that should be nested inside this one.
            help: (str | None): Help message to be displayed for the CLI; if not provided, class docstring will be used.
            extends (Typer  | CLI | None, optional): If provided, a typer instance or another CLI to add commands to.
            wraps (Any): Object to obtain CLI commands from. If not provided, self will be used.

        """
        self.options = options
        if isinstance(extends, Typer):
            self._typer = extends
        elif isinstance(extends, CLI):
            self._typer = extends.typer
        else:
            self._typer = Typer(
                name=self.options.name,
                no_args_is_help=True,
                add_help_option=True,
                help=help or (self.__doc__ if self.__doc__ != CLI.__doc__ else None),
            )
        self._children = children
        self._wraps = self if wraps is self._self else wraps
        self._setup_typer()

    @property
    def name(self) -> str:
        """
        Read only name attribute.

        Returns:
            str: The name of the CLI as provided at instantiation.

        """
        return self.options.name

    @property
    def command_names(self):
        """Return list of all CLI command names."""
        return tuple(command.name for command in self.typer.registered_commands)

    @property
    def typer(self) -> Typer:
        """
        Read only name attribute.

        Returns:
            Typer: the typer instance that the class wraps around, as generated or provided at instantiation.

        """
        return self._typer

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Run the CLI."""
        return self.typer(*args, **kwargs)

    def __getattr__(self, name: str):
        """
        Proxy unknown methods onto typer.

        This allows a CLI instance to be used precisely as a typer instance
        would be.
        """
        return getattr(self._typer, name)

    @staticmethod
    def _hidden_noop_callback():
        return None

    def _setup_typer(self):
        # Setting a callback overrides typer's default behaviour
        # which sets the a single command on the root of the CLI
        # It means the CLI behaves the same with one or several CLI options
        # which this author thinks is more predictable and explicit.

        self._typer.command("hidden", hidden=True)(self._hidden_noop_callback)
        for attr in dir(self._wraps):
            try:
                obj = getattr(self._wraps, attr)
            except Exception:
                # If there is an error on getattr, then it's likely the object
                # is a property or other descriptor object, and we can ignore it.
                continue
            if (
                attr[0] in string.ascii_letters
                and callable(obj)
                and getattr(obj, "__self__", None) is self._wraps
            ):
                _revise_annotations(obj.__func__)  # type: ignore
                command_name = _to_dash_case(obj.__name__)
                if command_name in self.command_names:
                    raise ConflictingCommandError(
                        f"cannot add CLI command with conflicting {command_name=}."
                    )
                if _is_callback(obj):
                    call_params = getattr(obj, _CALLBACK_KEY)
                    self.typer.callback(*call_params["args"], **call_params["kwargs"])(
                        obj
                    )
                else:
                    self.typer.command(command_name)(obj)
        for child in self._children:
            self.typer.add_typer(child.typer, name=child.name)
