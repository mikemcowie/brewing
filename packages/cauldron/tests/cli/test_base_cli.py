# ruff: noqa: T201
from __future__ import annotations

import string
from functools import partial
from typing import TYPE_CHECKING

from pydantic.alias_generators import to_snake
from typer import Typer
from typer.testing import CliRunner

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pytest_subtests import SubTests


def to_dash_case(value: str):
    return to_snake(value).replace("_", "-")


class CLI:
    def __init__(self, name: str, /, *children: CLI, typer: Typer | None = None):
        self._name = name
        self._typer = typer or Typer(name=name)
        self._children = children
        self._setup_typer()

    @property
    def name(self) -> str:
        return self._name

    @property
    def typer(self) -> Typer:
        return self._typer

    def _setup_typer(self):
        # Setting a callback overrides typer's default behaviour
        # which sets the a single command on the root of the CLI
        # It means the CLI behaves the same with one or several CLI options
        # which this author thinks is more predictable and explicit.
        self._typer.command("hidden")(lambda: None)
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


class CauldronCLIRunner:
    "Cauldron's wrapper around typer's CLIRunner"

    def __init__(
        self,
        cli: CLI,
        *,
        charset: str = "utf8",
        env: Mapping[str, str] | None = None,
        echo_stdin: bool = False,
        catch_exceptions: bool = False,
    ):
        env = env or {"NO_COLOR": "1"}
        self._runner = CliRunner(
            charset=charset,
            env=env,
            echo_stdin=echo_stdin,
            catch_exceptions=catch_exceptions,
        )
        self.invoke = partial(self._runner.invoke, cli.typer)


def test_basic_cli_with_one_cmd(subtests: SubTests):
    class SomeCLI(CLI):
        def do_something(self):
            """Allows you to do something"""
            print("something")

    runner = CauldronCLIRunner(SomeCLI("root"))
    with subtests.test("help"):
        result = runner.invoke(["--help"])
        assert result.exit_code == 0
        assert " Usage: root [OPTIONS] COMMAND [ARGS]..." in result.stdout
        assert "do-something   Allows you to do something" in result.stdout

    with subtests.test("something"):
        result = runner.invoke(["do-something"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "something"


def test_basic_cli_with_two_cmd(subtests: SubTests):
    class SomeCLI(CLI):
        def do_something(self):
            """Allows you to do something"""
            print("something")

        def also_something(self):
            """Also allows you to do something"""
            print("also")

    runner = CauldronCLIRunner(SomeCLI("root"))
    with subtests.test("help"):
        help_result = runner.invoke(["--help"], color=False)
        assert help_result.exit_code == 0
        assert " Usage: root [OPTIONS] COMMAND [ARGS]..." in help_result.stdout
        assert "do-something     Allows you to do something" in help_result.stdout
        assert "also-something   Also allows you to do something" in help_result.stdout
    with subtests.test("do-something"):
        result = runner.invoke(["do-something"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0
    with subtests.test("also-something"):
        result = runner.invoke(["also-something"])
        assert result.stdout.strip() == "also"
        assert result.exit_code == 0


def test_instance_attribute(subtests: SubTests):
    class SomeCLI(CLI):
        def __init__(self, name: str, message: str):
            self.message = message
            super().__init__(name)

        def quiet(self):
            """Allows you to do something"""
            print(self.message.lower())

        def loud(self):
            """Also allows you to do something"""
            print(self.message.upper())

    runner = CauldronCLIRunner(SomeCLI(name="root", message="Something"))

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0
    with subtests.test("loud"):
        result = runner.invoke(["loud"])
        assert result.stdout.strip() == "SOMETHING"
        assert result.exit_code == 0


def test_basic_parameter(subtests: SubTests):
    class SomeCLI(CLI):
        def speak(self, a_message: str):
            """Allows you to do speak"""
            print(a_message)

    runner = CauldronCLIRunner(SomeCLI("root"))

    with subtests.test("happy-path"):
        result = runner.invoke(["speak", "hello"])
        assert result.stdout.strip() == "hello"
        assert result.exit_code == 0

    with subtests.test("missing"):
        result = runner.invoke(["speak"])
        assert result.exit_code == 2
        assert "Missing argument 'A_MESSAGE" in result.stderr


def test_basic_option(subtests: SubTests):
    class SomeCLI(CLI):
        def speak(self, a_message: str = "hello"):
            """Allows you to do speak"""
            print(a_message)

    runner = CauldronCLIRunner(SomeCLI("root"))

    with subtests.test("wrong-invoke"):
        result = runner.invoke(["speak", "HI"])
        assert result.exit_code == 2
        assert "Got unexpected extra argument (HI)" in result.stderr, result.stderr

    with subtests.test("missing"):
        result = runner.invoke(["speak"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "hello"

    with subtests.test("provided"):
        result = runner.invoke(["speak", "--a-message", "HI"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "HI"


def test_nested_cli(subtests: SubTests):
    class Parent(CLI):
        def read(self):
            print("parent read")

        def write(self):
            print("parent write")

    class Child(CLI):
        def read(self):
            print("child read")

        def write(self):
            print("child write")

    cli = Parent("parent", Child("child"))
    runner = CauldronCLIRunner(cli)

    with subtests.test("parent-read"):
        result = runner.invoke(["read"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "parent read"

    with subtests.test("parent-write"):
        result = runner.invoke(["write"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "parent write"

    with subtests.test("child"):
        result = runner.invoke(["child"])
        assert "Usage: parent child [OPTIONS] COMMAND [ARGS]..." in result.stderr

    with subtests.test("child-read"):
        result = runner.invoke(["child", "read"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "child read"

    with subtests.test("parent-write"):
        result = runner.invoke(["child", "write"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "child write"
