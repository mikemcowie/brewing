# ruff: noqa: T201
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import typer
from brewinglib.cli import CLI, ConflictingCommandError
from brewinglib.cli.testing import BrewingCLIRunner

if TYPE_CHECKING:
    from pytest_subtests import SubTests


def test_basic_cli_with_one_cmd(subtests: SubTests):
    class SomeCLI(CLI):
        def do_something(self):
            """Allows you to do something"""
            print("something")

    runner = BrewingCLIRunner(SomeCLI("root"))
    with subtests.test("help"):
        result = runner.invoke(["--help"])
        assert result.exit_code == 0
        assert " [OPTIONS] COMMAND [ARGS]" in result.stdout
        assert "Allows you to do something" in result.stdout

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

    runner = BrewingCLIRunner(SomeCLI("root"))
    with subtests.test("help"):
        help_result = runner.invoke(["--help"], color=False)
        assert help_result.exit_code == 0
        assert "[OPTIONS] COMMAND [ARGS]" in help_result.stdout
        assert "Allows you to do something" in help_result.stdout
        assert "Also allows you to do something" in help_result.stdout
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

    runner = BrewingCLIRunner(SomeCLI(name="root", message="Something"))

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

    runner = BrewingCLIRunner(SomeCLI("root"))

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

    runner = BrewingCLIRunner(SomeCLI("root"))

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
    runner = BrewingCLIRunner(cli)

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
        assert "child [OPTIONS] COMMAND [ARGS]..." in result.stdout

    with subtests.test("child-read"):
        result = runner.invoke(["child", "read"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "child read"

    with subtests.test("parent-write"):
        result = runner.invoke(["child", "write"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "child write"


def test_cli_wraps_another_object(subtests: SubTests):
    class Something:
        def __init__(self, message: str):
            self.message = message

        def quiet(self):
            """Allows you to do something"""
            print(self.message.lower())

    something = Something(message="Something")
    cli = CLI("something", wraps=something)
    runner = BrewingCLIRunner(cli)

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0


def test_cli_extends_another(subtests: SubTests):
    class CLI1(CLI):
        def __init__(self, name: str, message: str):
            self.message = message
            super().__init__(name)

        def quiet(self):
            """Allows you to do something"""
            print(self.message.lower())

    class CLI2(CLI):
        def __init__(self, name: str, message: str, **kwargs: Any):
            self.message = message
            super().__init__(name, **kwargs)

        def loud(self):
            """Also allows you to do something"""
            print(self.message.upper())

    cli1 = CLI1(name="root", message="Something")
    cli2 = CLI2(name="root", message="Something", extends=cli1)
    runner = BrewingCLIRunner(cli2)

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0
    with subtests.test("loud"):
        result = runner.invoke(["loud"])
        assert result.stdout.strip() == "SOMETHING"
        assert result.exit_code == 0


def test_cli_a_typer(subtests: SubTests):
    app = typer.Typer()

    @app.command()
    def quiet():
        print("something")

    class CLI1(CLI):
        def __init__(self, name: str, message: str, **kwargs: Any):
            self.message = message
            super().__init__(name, **kwargs)

        def loud(self):
            """Also allows you to do something"""
            print(self.message.upper())

    cli2 = CLI1(name="root", message="Something", extends=app)
    runner = BrewingCLIRunner(cli2)

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0
    with subtests.test("loud"):
        result = runner.invoke(["loud"])
        assert result.stdout.strip() == "SOMETHING"
        assert result.exit_code == 0


def test_cannot_extend_with_conflicting_names(subtests: SubTests):
    class CLI1(CLI):
        def __init__(self, name: str, message: str):
            self.message = message
            super().__init__(name)

        def quiet(self):
            """Allows you to do something"""
            print(self.message.lower())

    class CLI2(CLI):
        def __init__(self, name: str, message: str, **kwargs: Any):
            self.message = message
            super().__init__(name, **kwargs)

        def quiet(self):
            """Also allows you to do something"""
            print(self.message.upper())

    cli1 = CLI1(name="root", message="Something")
    with pytest.raises(ConflictingCommandError) as error:
        CLI2(name="root", message="Something", extends=cli1)
    assert (
        "cannot add CLI command with conflicting command_name='quiet'."
        in error.exconly()
    )
