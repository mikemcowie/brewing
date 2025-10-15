"""
The entrypoint of the "brewing" binary.

We dynamically build a CLI based on the 'brewing' entrypoint of packages.
"""

import importlib.metadata
from typer import Typer
from brewing.cli import CLI


def load_entrypoint(entrypoint: importlib.metadata.EntryPoint) -> CLI:
    obj = entrypoint.load()
    error = TypeError(
        f"{obj!r} is not suitable as a brewing entrypoint, it must be a brewing.cli.CLI instance or a callable returning such."
    )
    if isinstance(obj, CLI):
        return obj
    if not callable(obj):
        raise error
    obj = obj()
    if isinstance(obj, CLI):
        return obj
    raise error


def cli():
    cli = CLI("brewing", extends=Typer())
    entrypoints = importlib.metadata.entry_points(group="brewing")
    for entrypoint in entrypoints:
        cli.add_typer(load_entrypoint(entrypoint).typer, name=entrypoint.name)
    return cli


def run():
    cli()()
