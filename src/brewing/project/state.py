"""Project inialization functionality."""

import sys
from textwrap import dedent

import structlog
import tomlkit
from pydantic import RootModel, alias_generators

from brewing.project import pyproject
from brewing.project.generation import (
    Directory,
    ManagedDirectory,
    ProjectConfiguration,
    materialize_directory,
)

logger = structlog.get_logger()


def empty_file_content(context: ProjectConfiguration):  # noqa: ARG001
    """Return an empty file content."""
    return ""


def initial_app_file(context: ProjectConfiguration):  # noqa: ARG001
    """Return the content of the initial app.py file."""
    return dedent(
        """

        # ruff: noqa: PLC0415
        from pathlib import Path

        from brewing import Brewing
        from brewing.db import Database, new_base
        from brewing.db.settings import PostgresqlSettings
        from brewing.http import BrewingHTTP

        # register database models by inheriting from this base.
        # brewing will automatically scan for modules inheriting from this
        # while starting up, to ensure consistent database metadadta.
        Base = new_base()

        def app():
            "Application loading callable."
            # Add your own imports here.
            # Imports in functiom scope will be needed if you
            # Have any models inheriting from Base outside of this file.
            from brewing.healthcheck.viewset import HealthCheckViewset

            return Brewing(
            name="generated-project",
            database=Database(
                metadata=Base.metadata,
                revisions_directory=Path(__file__).parent / "db_revisions",
                config_type=PostgresqlSettings,
            ),
            components={"http": BrewingHTTP(viewsets=[HealthCheckViewset()])},
        )


    """
    )


_PLACEHOLDER_PROJECT_NAME = "{PROJECT_NAME}"


def load_pyproject_content(context: ProjectConfiguration):
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


def project_name_with_underscores(context: ProjectConfiguration):
    """Return project name in form suitable for python attributes."""
    return alias_generators.to_snake(context.name)


def init_layout() -> Directory:
    """Return the layout for project initialization."""
    return {
        "pyproject.toml": load_pyproject_content,
        "README.md": empty_file_content,
        ".gitignore": empty_file_content,
        "src": {
            project_name_with_underscores: {
                "__init__.py": empty_file_content,
                "app.py": initial_app_file,
            }
        },
    }


def init(context: ProjectConfiguration):
    """Initialize the project."""
    materialize_directory(ManagedDirectory(files=init_layout(), config=context))
