# ruff: noqa: T201
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

import pytest
import typer
from typer import Argument

from brewing.cli import CLI, CLIOptions, ConflictingCommandError, callback
from brewing.cli.testing import BrewingCLIRunner

if TYPE_CHECKING:
    from pytest_subtests import SubTests


@pytest.fixture(autouse=True)
def no_color(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NO_COLOR", "1")


def test_basic_cli_with_one_cmd(subtests: SubTests):
    class SomeCLI(CLI[CLIOptions]):
        def do_something(self):
            """Allows you to do something"""
            print("something")

    runner = BrewingCLIRunner(SomeCLI(CLIOptions("root")))
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
    class SomeCLI(CLI[CLIOptions]):
        def do_something(self):
            """Allows you to do something"""
            print("something")

        def also_something(self):
            """Also allows you to do something"""
            print("also")

    runner = BrewingCLIRunner(SomeCLI(CLIOptions("root")))
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
    @dataclass
    class Options:
        name: str
        message: str

    class SomeCLI(CLI[Options]):
        def quiet(self):
            """Allows you to do something"""
            print(self.options.message.lower())

        def loud(self):
            """Also allows you to do something"""
            print(self.options.message.upper())

    runner = BrewingCLIRunner(SomeCLI(Options(name="root", message="Something")))

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0
    with subtests.test("loud"):
        result = runner.invoke(["loud"])
        assert result.stdout.strip() == "SOMETHING"
        assert result.exit_code == 0


def test_basic_option(subtests: SubTests):
    class SomeCLI(CLI[CLIOptions]):
        def speak(self, a_message: str):
            """Allows you to do speak"""
            print(a_message)

    runner = BrewingCLIRunner(SomeCLI(CLIOptions(name="root")))

    with subtests.test("happy-path"):
        result = runner.invoke(["speak", "--a-message", "hello"])
        assert result.exit_code == 0, result.stderr
        assert result.stdout.strip() == "hello"

    with subtests.test("missing"):
        result = runner.invoke(["speak"], color=False)
        assert result.exit_code == 2
        assert "Missing option" in result.output, result.output


def test_basic_argument(subtests: SubTests):
    class SomeCLI(CLI[CLIOptions]):
        def speak(self, a_message: Annotated[str, Argument()]):
            """Allows you to do speak"""
            print(a_message)

    runner = BrewingCLIRunner(SomeCLI(CLIOptions(name="root")))

    with subtests.test("happy-path"):
        result = runner.invoke(["speak", "hello"])
        assert result.exit_code == 0, result.stderr
        assert result.stdout.strip() == "hello"

    with subtests.test("missing"):
        result = runner.invoke(["speak"])
        assert result.exit_code == 2
        assert "Missing argument 'A_MESSAGE" in result.stderr, result.stderr


def test_positional_parameter():
    class SomeCLI(CLI[CLIOptions]):
        def speak(self, a_message: str, /):
            """Allows you to do speak"""
            print(a_message)  # pragma: no cover

    with pytest.raises(TypeError) as error:
        SomeCLI(CLIOptions(name="root"))
    assert "Cannot support positional-only arguments." in error.exconly()


def test_with_default(subtests: SubTests):
    class SomeCLI(CLI[CLIOptions]):
        def speak(self, a_message: str = "hello"):
            """Allows you to do speak"""
            print(a_message)

    runner = BrewingCLIRunner(SomeCLI(CLIOptions(name="root")))

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
    class Parent(CLI[CLIOptions]):
        def read(self):
            print("parent read")

        def write(self):
            print("parent write")

    class Child(CLI[CLIOptions]):
        def read(self):
            print("child read")

        def write(self):
            print("child write")

    cli = Parent(CLIOptions(name="parent"), Child(CLIOptions("child")))
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
    cli = CLI(CLIOptions("something"), wraps=something)
    runner = BrewingCLIRunner(cli)

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0


def test_cli_extends_another(subtests: SubTests):
    @dataclass
    class Options:
        name: str
        message: str

    class CLI1(CLI[Options]):
        def quiet(self):
            """Allows you to do something"""
            print(self.options.message.lower())

    class CLI2(CLI[Options]):
        def loud(self):
            """Also allows you to do something"""
            print(self.options.message.upper())

    cli1 = CLI1(Options(name="root", message="Something"))
    cli2 = CLI2(Options(name="root", message="Something"), extends=cli1)
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

    @dataclass
    class Options:
        name: str
        message: str

    class CLI1(CLI[Options]):
        def loud(self):
            """Also allows you to do something"""
            print(self.options.message.upper())

    cli2 = CLI1(Options(name="root", message="Something"), extends=app)
    runner = BrewingCLIRunner(cli2)

    with subtests.test("quiet"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "something"
        assert result.exit_code == 0
    with subtests.test("loud"):
        result = runner.invoke(["loud"])
        assert result.stdout.strip() == "SOMETHING"
        assert result.exit_code == 0


def test_cannot_extend_with_conflicting_names():
    @dataclass
    class Options:
        name: str
        message: str

    class CLI1(CLI[Options]):
        def quiet(self):
            """Allows you to do something"""
            print(self.options.message.lower())  # pragma: no cover

    class CLI2(CLI[Options]):
        def quiet(self):
            """Also allows you to do something"""
            print(self.options.message.upper())  # pragma: no cover

    cli1 = CLI1(Options(name="root", message="Something"))
    with pytest.raises(ConflictingCommandError) as error:
        CLI2(Options(name="root", message="Something"), extends=cli1)
    assert (
        "cannot add CLI command with conflicting command_name='quiet'."
        in error.exconly()
    )


def test_callback(subtests: SubTests):
    @dataclass
    class Options:
        name: str
        message: str

    class CLI1(CLI[Options]):
        @callback()
        def initial(self):
            """First noise."""
            print("calling back!")

        def quiet(self):
            """Allows you to do something"""
            print(self.options.message.lower())

    cli = CLI1(Options(name="root", message="Something"))
    runner = BrewingCLIRunner(cli)

    assert "quiet" in cli.command_names
    assert "initial" not in cli.command_names

    with subtests.test("help"):
        result = runner.invoke(["--help"])
        assert "quiet" in result.output
        assert "initial" not in result.output

    with subtests.test("cmd"):
        result = runner.invoke(["quiet"])
        assert result.stdout.strip() == "calling back!\nsomething"
        assert result.exit_code == 0
