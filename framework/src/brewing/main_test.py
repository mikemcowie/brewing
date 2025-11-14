"""Tests of the main module"""

import pytest
from pytest_subtests import SubTests
from textwrap import dedent
from typing import cast
from typer import Typer
from unittest.mock import MagicMock
from pathlib import Path
from brewing import main, CLI, CLIOptions
from importlib.metadata import EntryPoint


def new_options() -> main.BrewingOptions[MagicMock]:
    """return a fake options instance."""
    return main.BrewingOptions(name="test", database=MagicMock())


def test_brewing_options_global_loaded(subtests: SubTests):
    """Error raised if we try to retrieve the options without entering a context."""
    with (
        subtests.test("no-instance-created-raises"),
        pytest.raises(main.NoCurrentOptions),
    ):
        main.BrewingOptions.current()
    options = new_options()
    with (
        subtests.test("instance-created-not_entered_raises"),
        pytest.raises(main.NoCurrentOptions),
    ):
        main.BrewingOptions.current()
    with subtests.test("instance-entered"), options:
        assert main.BrewingOptions.current() is options
    with subtests.test("raises-after-exit"), pytest.raises(main.NoCurrentOptions):
        assert main.BrewingOptions.current()


# pyright: reportUnusedExpression=false


def test_brewing(subtests: SubTests):
    """Test the setup of the Brewing class."""
    comp1 = MagicMock()
    comp2 = MagicMock()
    options = new_options()
    with options:
        app = main.Brewing(comp1=comp1, comp2=comp2)
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

        app.comp1 is comp1
        app.comp2 is comp2
        app.db is options.database

    with (
        subtests.test("__getattr__ fails on arbitart attr"),
        pytest.raises(AttributeError),
    ):
        app.foo_bar


def sample_entrypoints():
    return [
        EntryPoint(name="foo", value="foo.bar:cheese", group="brewing"),
        EntryPoint(name="bar", value="bar.onions", group="brewing"),
        EntryPoint(name="something-else", value="something.else:here", group="boop"),
    ]


def test_main_cli_brewing_entrypoints_matched():
    """package entrypoints from brewing group are matched."""
    cli = main.main_cli(
        entrypoints=sample_entrypoints(),
        entrypoint_loader=lambda _: CLI(CLIOptions(name="foo")),
    )
    assert set(c.name for c in cli.typer.registered_commands) == {"hidden"}
    assert set(c.name for c in cli.typer.registered_groups) == {"foo", "bar"}


def test_main_cli_brewing_entrypoints_of_current_project_added_to_root_cli():
    """If we are in project foo, foo's CLI commands will be added to the root CLI."""

    class FooCLI(CLI[CLIOptions]):
        def foo1(self):
            """ "Some CLI command."""

    cli = main.main_cli(
        entrypoints=sample_entrypoints(),
        entrypoint_loader=lambda _: FooCLI(CLIOptions(name="foo")),
        project_provider=lambda: "foo",
    )
    unnamed_groups = [g for g in cli.typer.registered_groups if not g.name]
    assert len(unnamed_groups) == 1
    assert set(
        c.name
        for c in cast(Typer, unnamed_groups[0].typer_instance).registered_commands
    ) == {"hidden", "foo-1"}


def test_load_current_project(tmp_path: Path, subtests: SubTests):
    with subtests.test("finds-parent-dir"):
        nested_search_dir = tmp_path / "parent-test" / "level1" / "level2" / "level3"
        nested_search_dir.mkdir(parents=True)
        (nested_search_dir.parents[1] / "pyproject.toml").write_text(
            dedent(
                """
            [project]
            name = "foo"
            """
            )
        )
        assert main.current_project(nested_search_dir) == "foo"

    with subtests.test("raises-no-project-name"):
        nested_search_dir = tmp_path / "no-name-test" / "level1" / "level2" / "level3"
        nested_search_dir.mkdir(parents=True)
        (nested_search_dir.parents[1] / "pyproject.toml").write_text(
            dedent(
                """
            [project]
            """
            )
        )
        with pytest.raises(ValueError) as err:
            main.current_project(nested_search_dir)
        assert "No project.name in file=" in err.exconly()

    with subtests.test("not-in-project"):
        assert main.current_project(tmp_path) is None


def test_entrypoint_load(subtests: SubTests):
    entrypoint = MagicMock()
    load = MagicMock()
    entrypoint.load = load
    with subtests.test("error-on-not-valid-type"):
        load.return_value = ""
        with pytest.raises(TypeError):
            main.load_entrypoint(entrypoint)
    with subtests.test("CLI instance"):
        cli = CLI(CLIOptions(name="foo"))
        load.return_value = cli
        assert main.load_entrypoint(entrypoint) is cli
    with subtests.test("callable giving a CLI instance"):
        cli = CLI(CLIOptions(name="foo"))
        load.return_value = lambda: cli
        assert main.load_entrypoint(entrypoint) is cli
    with subtests.test("callable giving wrong type"):
        load.return_value = lambda: ""
        with pytest.raises(TypeError):
            main.load_entrypoint(entrypoint)
