"""
The core project CLI.

This is the main brewing CLI that manages project, similar
to the rails CLI for rails or manage.py for django.
"""

from typing import Callable, Annotated
from dataclasses import dataclass
from brewing.cli import CLI
from pathlib import Path
from typer import Option
import structlog


logger = structlog.get_logger()


@dataclass
class InitContext:
    name: str
    path: Path
    force: bool


def empty_file_content(context: InitContext):
    return ""


PROJECT_NAME_WITH_UNDERSCORES = "{PROJECT_NAME}"


def write_initial_files(context: InitContext):
    files: dict[Path, Callable[[InitContext], str]] = {
        Path("pyproject.toml"): empty_file_content,
        Path(".gitignore"): empty_file_content,
        Path("src", PROJECT_NAME_WITH_UNDERSCORES, "__init__.py"): empty_file_content,
        Path("src", PROJECT_NAME_WITH_UNDERSCORES, "app.py"): empty_file_content,
    }
    for file, content_generator in files.items():
        file = Path(
            *[
                part.replace(
                    PROJECT_NAME_WITH_UNDERSCORES, context.name.replace("-", "_")
                )
                for part in file.parts
            ]
        )
        if file.is_absolute():
            raise ValueError(
                f"File path {file=!s} was provided as an absolute path, but a relative path is required."
            )
        out_path = context.path / file
        out_path.parent.mkdir(exist_ok=True, parents=True)
        content = content_generator(context)
        if not context.force and out_path.exists():
            raise FileExistsError(
                f"Cannot generate {out_path=!s} as it already exists."
            )
        out_path.write_text(content)


class ProjectCLI(CLI):
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
        path = path.resolve()
        name = name or path.name
        context = InitContext(name=name, path=path, force=force)
        logger.info(f"Initializing project with options {context}")
        write_initial_files(context=context)


def load() -> ProjectCLI:
    return ProjectCLI("project")


if __name__ == "__main__":
    load()()
