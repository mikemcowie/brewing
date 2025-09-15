# Embed the alembic CLI in a typer CLI
import sys
from functools import cached_property
from pathlib import Path

import typer
from alembic import command
from alembic.config import CommandLine, Config
from brewing import CLI


class Migrations(CLI):
    def __init__(self, name: str, /, *children: CLI):
        super().__init__(name, *children)

        # Want a first-class way to define context
        # Instead of having to define a nested function.
        @self.typer.command(context_settings={"allow_extra_args": True})
        def alembic(context: typer.Context):
            """Executes the command line with the provided arguments."""
            ## Copied and adapted from alenbic.config.Commandline.main
            cmd = CommandLine(" ".join(sys.argv[: -len(context.args)] + context.args))
            options = cmd.parser.parse_args(context.args)
            if not hasattr(options, "cmd"):
                # see http://bugs.python.org/issue9253, argparse
                # behavior changed incompatibly in py3.3
                cmd.parser.error("too few arguments")
            else:
                cmd.run_cmd(self.config, options)

    @cached_property
    def config(self):
        config = Config()
        config.set_main_option(
            "script_location", str(Path(__file__).parent / "migrations")
        )
        config.set_main_option(
            "version_locations", str(Path(__file__).parent / "versions")
        )
        return config

    def upgrade(self, revision: str = "head"):
        """Upgrade the database to specified revision."""
        command.upgrade(self.config, revision=revision)


Migrations("db")()
