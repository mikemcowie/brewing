from __future__ import annotations
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from brewing import CLI, CLIOptions, plugin

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_subtests import SubTests


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
        assert plugin.current_project(nested_search_dir) == "foo"

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
            plugin.current_project(nested_search_dir)
        assert "No project.name in file=" in err.exconly()

    with subtests.test("not-in-project"):
        assert plugin.current_project(tmp_path) is None


def test_entrypoint_load(subtests: SubTests):
    entrypoint = MagicMock()
    load = MagicMock()
    entrypoint.load = load
    with subtests.test("error-on-not-valid-type"):
        load.return_value = ""
        with pytest.raises(TypeError):
            plugin.load_entrypoint(entrypoint)
    with subtests.test("CLI instance"):
        cli = CLI(CLIOptions(name="foo"))
        load.return_value = cli
        assert plugin.load_entrypoint(entrypoint) is cli
    with subtests.test("callable giving a CLI instance"):
        cli = CLI(CLIOptions(name="foo"))
        load.return_value = lambda: cli
        assert plugin.load_entrypoint(entrypoint) is cli
    with subtests.test("callable giving wrong type"):
        load.return_value = lambda: ""
        with pytest.raises(TypeError):
            plugin.load_entrypoint(entrypoint)
