"""
In typer, if no explicit annotation of an option vs argument is provided
then function args without a default become arguments
and function  args with defaults become options.
"""

from __future__ import annotations

from typer import Typer
from typer.testing import CliRunner

app = Typer(no_args_is_help=True)


@app.command()
def something(no_default: str, has_default: str = "default"):
    print(f"{no_default=} {has_default=}")


result = CliRunner().invoke(app, ["--help"])
print("running default typer behaviour")
print(result.stdout)
print(f"{'something [OPTIONS] NO_DEFAULT' in result.stdout=}")
print(f"{'--has-default' in result.stdout=}")

"""But IMO a better API would be to tie it to python's positional-only vs keyword arguments

positional-only arguments correspond to CLI arguments
kw-only or kw-or-positional arguments should both correspond to CLI options.

This slightly more favors towards options than arguments, which I think is a good thing.
"""

app = Typer(no_args_is_help=True)


@app.command()
def something(positional_only: int, /, kw_or_positional: int, *, kw_only: int):
    print(f"{positional_only=} {kw_or_positional=} {kw_only=}")


result = CliRunner().invoke(app, ["--help"])
print("running func with 3 types of args")
print(result.stdout)
print(":( Usage: something [OPTIONS] POSITIONAL_ONLY KW_OR_POSITIONAL KW_ONLY ")


"""How do we hack typer to make the 2nd and 3rd function args into cli options?

Basically, we need to edit the runtime annotations of this function to show typer
explicit Options / Argument configuration matching the behaviour we want.
"""


def something(positional_only: int, /, kw_or_positional: int, *, kw_only: int):
    print(f"{positional_only=} {kw_or_positional=} {kw_only=}")


from typing import Annotated

from typer import Argument, Option

print(something.__annotations__)
something.__annotations__["kw_or_positional"] = Annotated[int, Option()]
something.__annotations__["kw_only"] = Annotated[int, Option()]

app = Typer()
app.command()(something)
result = CliRunner().invoke(app, ["--help"])
print("running func after editing its annotations")
print(result.stdout)

"""That was enough! Just need to automate it better.

Let's do it again, but this time we'll use get_type_hints and inspect to automate the decision-making."""
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from typer.models import ArgumentInfo, OptionInfo


def something(positional_only: int, /, kw_or_positional: int, *, kw_only: int):
    print(f"{positional_only=} {kw_or_positional=} {kw_only=}")


def revise_annotation(param: inspect.Parameter) -> Any:
    if param.kind in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL):
        return Annotated[param.annotation, Argument()]
    else:
        return Annotated[param.annotation, Option()]


def revise_annotations(func: Callable):
    args = inspect.signature(func, eval_str=True)
    current = {
        name: {"kind": param.kind, "annotation": param.annotation}
        for name, param in args.parameters.items()
    }
    revised = {
        name: {"kind": param.kind, "annotation": revise_annotation(param)}
        for name, param in args.parameters.items()
    }
    print(f"{current=}")
    print(f"{revised=}")
    func.__annotations__ = {
        name: revise_annotation(param) for name, param in args.parameters.items()
    }


revise_annotations(something)

app = Typer()
app.command()(something)
result = CliRunner().invoke(app, ["--help"])
print("take 2 at running func after editing its annotations")
print(result.stdout)


"""That works! Now we just need to deal with cases where there's already an Option or Argument annotation. This should override the implicit behaviour."""


def something(
    positional_only: int,
    positional_overriden_to_option: Annotated[int, Option()],
    /,
    kw_or_positional: int,
    kw_or_positional_overridden_to_arg: Annotated[int, Argument()],
    *,
    kw_only: int,
):
    print(
        f"{positional_only=} {kw_or_positional=} {kw_only=} {positional_overriden_to_option=}, {kw_or_positional_overridden_to_arg}"
    )


@dataclass
class Annotation:
    """A view of the data provided by inspect.signature and get_type_hints"""

    origin: Any
    metadata: tuple[Any, ...]
    is_positional_only: bool


def revise_annotation(func: Callable, param: inspect.Parameter, type_hint: Any) -> Any:
    if type_hint is None:
        raise RuntimeError(f"{func=} has no type hint or type hint is None")
    metadata = getattr(type_hint, "__metadata__", ())
    if metadata and [
        item for item in metadata if isinstance(item, (OptionInfo, ArgumentInfo))
    ]:
        # The item is already annotated with typer annotions, return it unchanged
        return param.annotation

    if param.kind in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL):
        typer_param_type = Argument
    else:
        typer_param_type = Option
    return Annotated[param.annotation, *(metadata + (typer_param_type(),))]


def revise_annotations(func: Callable):
    type_hints = get_type_hints(
        func, include_extras=True
    )  # Needed for the values of annotations
    func.__annotations__ = {
        name: revise_annotation(func, param, type_hints.get(name))
        for name, param in inspect.signature(func, eval_str=True).parameters.items()
    }


revise_annotations(something)

app = Typer()
app.command()(something)
result = CliRunner().invoke(app, ["--help"])
print("take 3 at running func after editing its annotations")
print(result.stdout)


"""And that's basically it!! The pattern to be applied to the CLI class!"""
