"""Project inialization functionality."""

import sys
from typing import Callable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
import structlog
import tomlkit
from brewing.project import pyproject
from pydantic import RootModel


logger = structlog.get_logger()


@dataclass
class InitContext:
    """Shared context for the project initialization."""

    name: str
    path: Path
    force: bool


def empty_file_content(context: InitContext):
    """Return an empty file content."""
    return ""


def initial_app_file(context: InitContext):
    """Return the content of the initial app.py file."""
    return dedent(
        """

    from pathlib import Path

    from brewing import Brewing
    from brewing.db import Database, new_base
    from brewing.db.settings import PostgresqlSettings
    from brewing.healthcheck.viewset import HealthCheckOptions, HealthCheckViewset
    from brewing.http import BrewingHTTP
    from brewing.app import BrewingOptions

    # register database models by inheriting from this base.
    # brewing will automatically scan for modules inheriting from this
    # while starting up, to ensure consistent database metadadta.
    Base = new_base()

    # construct the application by providing the settings and components that make up the app.
    with BrewingOptions(
        name="generated-project",
        database=Database[PostgresqlSettings](
            metadata=Base.metadata,
            revisions_directory=Path(__file__).parent / "db_revisions",
        )
    ):
        app = Brewing(
            http=BrewingHTTP().with_viewsets(HealthCheckViewset(HealthCheckOptions())),
        )


    def __getattr__(name:str):
        return getattr(app, name)

    """
    )


_PLACEHOLDER_PROJECT_NAME = "{PROJECT_NAME}"


def load_pyproject_content(context: InitContext):
    """Load the pyproject.toml file."""
    return tomlkit.dumps(
        pyproject.PyprojectTomlData(
            project=pyproject.Project(
                name=context.name,
                version="0.0.1",
                requires_python=f">={sys.version_info.major}.{sys.version_info.minor}",
                dependencies=["brewing", "psycopg[binary]"],
                readme="README.md",
                entry_points=RootModel(
                    root={
                        "brewing": {
                            context.name: f"{context.name.replace('-', '_')}.app:app"
                        }
                    }
                ),
            ),
            build_system=pyproject.BuildSystem(
                requires=["hatchling"], build_backend="hatchling.build"
            ),
        ).model_dump(mode="json", exclude_none=True, by_alias=True)
    )


def write_initial_files(context: InitContext):
    """Write the initial files of the project."""
    logger.info(f"Initializing project with options {context}")
    files: dict[Path, Callable[[InitContext], str]] = {
        Path("pyproject.toml"): load_pyproject_content,
        Path("README.md"): empty_file_content,
        Path(".gitignore"): empty_file_content,
        Path("src", _PLACEHOLDER_PROJECT_NAME, "__init__.py"): empty_file_content,
        Path("src", _PLACEHOLDER_PROJECT_NAME, "app.py"): initial_app_file,
    }
    for file, content_generator in files.items():
        file = Path(
            *[
                part.replace(_PLACEHOLDER_PROJECT_NAME, context.name.replace("-", "_"))
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
        if not context.force and out_path.exists() and list(out_path.glob("**/*.py")):
            raise FileExistsError(
                f"Cannot generate {out_path=!s} as it already exists."
            )
        out_path.write_text(content)
