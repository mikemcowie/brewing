"""Tests of the main module"""

import pytest
from pytest_subtests import SubTests
from unittest.mock import MagicMock
from brewing import main


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
