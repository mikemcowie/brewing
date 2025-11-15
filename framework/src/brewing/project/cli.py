"""
The core project CLI.

This is the main brewing CLI that manages project, similar
to the rails CLI for rails or manage.py for django.
"""

from typing import Annotated
from brewing.cli import CLI, CLIOptions
from pathlib import Path
from typer import Option
import structlog
from brewing.project.initialization import InitContext, write_initial_files


logger = structlog.get_logger()


class ProjectCLI(CLI[CLIOptions]):
    """
    Manages a brewing project.

    Development functionality to begin or modify brewing projects.
    """

    def init(
        self,
        name: Annotated[
            str | None,
            Option(
                help="The name of the project. If not provided, the directory name will be used."
            ),
        ] = None,
        path: Annotated[
            Path, Option(help="The path the initialize the project in.")
        ] = Path.cwd(),
        force: Annotated[
            bool, Option(help="Force overwrite any existing files.")
        ] = False,
    ):
        """Initialize a new brewing project."""
        context = InitContext(name=name or path.name, path=path.resolve(), force=force)
        write_initial_files(context=context)


def load() -> ProjectCLI:
    """Instantiate the project CLI."""
    return ProjectCLI(CLIOptions(name="project"))
