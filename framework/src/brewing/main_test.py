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
