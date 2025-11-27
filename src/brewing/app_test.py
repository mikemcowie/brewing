"""Tests of the main module"""

from __future__ import annotations

import pickle
from importlib.metadata import EntryPoint
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from sqlalchemy import MetaData

import brewing.plugin
from brewing import CLI, CLIOptions, plugin
from brewing.app import Brewing
from brewing.db import Database
from brewing.db import testing as db_testing
from brewing.db.settings import DatabaseType, SQLiteSettings
from brewing.healthcheck.viewset import HealthCheckViewset
from brewing.http import BrewingHTTP

if TYPE_CHECKING:
    from pytest_subtests import SubTests
    from typer import Typer


# pyright: reportUnusedExpression=false


def test_brewing(subtests: SubTests):
    """Test the setup of the Brewing class."""
    comp1 = MagicMock()
    comp2 = MagicMock()
    db = MagicMock()
    app = Brewing(name="test", database=db, components={"comp1": comp1, "comp2": comp2})
    with subtests.test("components-attribute"):
        assert app.all_components == {"comp1": comp1, "comp2": comp2, "db": db}
    with subtests.test("components-registered"):
        comp1.register.assert_called_once_with("comp1", app)
        comp2.register.assert_called_once_with("comp2", app)
        db.register.assert_called_once_with("db", app)  # type: ignore


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


metadata = MetaData()


def test_brewing_with_pickle_roundtrip(subtests: SubTests):
    """A brewing instance can be reproduced via a roundtrip through pickle."""

    def round_trip(obj: Any):
        """Return a copy of obj that has been pickled and unpickled."""
        return pickle.loads(pickle.dumps(obj))

    with db_testing.testing(DatabaseType.sqlite):
        database = Database(metadata=metadata, config_type=SQLiteSettings)

        with subtests.test("empty-case"):
            app = Brewing(name="test", database=database, components={})
            before = app
            after = round_trip(app)
            assert before is not after
            assert before == after

        with subtests.test("empty-http"):
            app = Brewing(
                name="test",
                database=database,
                components={"http": BrewingHTTP(viewsets=[])},
            )
            before = app
            after = round_trip(app)
            assert before is not after
            assert before == after

        with subtests.test("with-viewset"):
            app = Brewing(
                name="test",
                database=database,
                components={"http": BrewingHTTP(viewsets=[HealthCheckViewset()])},
            )
            before = app
            after = round_trip(app)
            assert before is not after
            assert before == after
