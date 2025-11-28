"""
The core project CLI.

This is the main brewing CLI that manages project, similar
to the rails CLI for rails or manage.py for django.
"""

from pathlib import Path
from typing import Annotated

import structlog
from typer import Option

from brewing.cli import CLI, CLIOptions
from brewing.db import DatabaseType  # noqa: TC001
from brewing.project.generation import ProjectConfiguration
from brewing.project.state import init

logger = structlog.get_logger()


class ProjectCLI(CLI[CLIOptions]):
    """
    Manages a brewing project.

    Development functionality to begin or modify brewing projects.
    """

    def init(
        self,
        db_type: Annotated[
            DatabaseType, Option(help="database type to initialize for.")
        ],
        name: Annotated[
            str | None,
            Option(
                help="The name of the project. If not provided, the directory name will be used."
            ),
        ] = None,
        path: Annotated[
            Path | None, Option(help="The path the initialize the project in.")
        ] = None,
    ):
        """Initialize a new brewing project."""
        path = path or Path.cwd()
        config = ProjectConfiguration(
            name=name or path.name, path=path.resolve(), db_type=db_type
        )
        logger.info("generating project skeleton", config=config)
        init(config)


def load() -> ProjectCLI:
    """Instantiate the project CLI."""
    return ProjectCLI(CLIOptions(name="project"))
