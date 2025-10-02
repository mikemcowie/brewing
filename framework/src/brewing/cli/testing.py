"""Brewing CLI testing helper."""

from collections.abc import Mapping
from functools import partial

from typer.testing import CliRunner

from .cli import CLI


class BrewingCLIRunner:
    """Brewing's wrapper around typer's CLIRunner."""

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
