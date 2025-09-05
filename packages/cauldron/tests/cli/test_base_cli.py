# ruff: noqa: T201
import string
from collections.abc import Mapping
from functools import partial

from pydantic.alias_generators import to_snake
from pytest_subtests import SubTests
from typer import Typer
from typer.testing import CliRunner


def to_dash_case(value: str):
    return to_snake(value).replace("_", "-")


class CLI:
    def __init__(self, /, typer: Typer | None = None):
        self._typer = typer or Typer()
        self._setup_typer()

    @property
    def typer(self):
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

    runner = CauldronCLIRunner(SomeCLI())
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

    runner = CauldronCLIRunner(SomeCLI())
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
