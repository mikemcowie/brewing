"""Tests of the main module"""

from __future__ import annotations

from importlib.metadata import EntryPoint
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest

import brewing.plugin
from brewing import CLI, CLIOptions, plugin
from brewing.app import Brewing, BrewingOptions, NoCurrentOptions

if TYPE_CHECKING:
    from pytest_subtests import SubTests
    from typer import Typer


def new_options() -> BrewingOptions[MagicMock]:
    """return a fake options instance."""
    return BrewingOptions(name="test", database=MagicMock())


def test_brewing_options_global_loaded(subtests: SubTests):
    """Error raised if we try to retrieve the options without entering a context."""
    with (
        subtests.test("no-instance-created-raises"),
        pytest.raises(NoCurrentOptions),
    ):
        BrewingOptions.current()
    options = new_options()
    with (
        subtests.test("instance-created-not_entered_raises"),
        pytest.raises(NoCurrentOptions),
    ):
        BrewingOptions.current()
    with subtests.test("instance-entered"), options:
        assert BrewingOptions.current() is options
    with subtests.test("raises-after-exit"), pytest.raises(NoCurrentOptions):
        assert BrewingOptions.current()


# pyright: reportUnusedExpression=false


def test_brewing(subtests: SubTests):
    """Test the setup of the Brewing class."""
    comp1 = MagicMock()
    comp2 = MagicMock()
    options = new_options()
    with options:
        app = Brewing(comp1=comp1, comp2=comp2)
    with subtests.test("components-attribute"):
        assert app.components == {
            "comp1": comp1,
            "comp2": comp2,
            "db": options.database,
        }
    with subtests.test("components-registered"):
        comp1.register.assert_called_once_with("comp1", app)
        comp2.register.assert_called_once_with("comp2", app)
        options.database.register.assert_called_once_with("db", app)  # type: ignore
    with subtests.test("components-available-as-attributes"):
        ## components are available as dynamic attributes.
        # this allows an entrypoint module to use module-level __getattr__ to expose them.

        assert app.comp1 is comp1
        assert app.comp2 is comp2
        assert app.db is options.database

    with (
        subtests.test("__getattr__ fails on arbitart attr"),
        pytest.raises(AttributeError),
    ):
        app.foo_bar  # noqa: B018


def sample_entrypoints():
    return [
        EntryPoint(name="foo", value="foo.bar:cheese", group="brewing"),
        EntryPoint(name="bar", value="bar.onions", group="brewing"),
        EntryPoint(name="something-else", value="something.else:here", group="boop"),
    ]


def test_main_cli_brewing_entrypoints_matched():
    """package entrypoints from brewing group are matched."""
    cli = brewing.plugin.main_cli(
        entrypoints=sample_entrypoints(),
        entrypoint_loader=lambda _: CLI(CLIOptions(name="foo")),
    )
    assert {c.name for c in cli.typer.registered_commands} == {"hidden"}
    assert {c.name for c in cli.typer.registered_groups} == {"foo", "bar"}


def test_main_cli_brewing_entrypoints_of_current_project_added_to_root_cli():
    """If we are in project foo, foo's CLI commands will be added to the root CLI."""

    class FooCLI(CLI[CLIOptions]):
        def foo1(self):
            """ "Some CLI command."""

    cli = plugin.main_cli(
        entrypoints=sample_entrypoints(),
        entrypoint_loader=lambda _: FooCLI(CLIOptions(name="foo")),
        project_provider=lambda: "foo",
    )
    unnamed_groups = [g for g in cli.typer.registered_groups if not g.name]
    assert len(unnamed_groups) == 1
    assert {
        c.name
        for c in cast("Typer", unnamed_groups[0].typer_instance).registered_commands
    } == {"hidden", "foo-1"}
