import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
import yaml  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]

from project_manager.db import Database

cli = typer.Typer(add_help_option=True, no_args_is_help=True)
dev = typer.Typer(add_help_option=True, no_args_is_help=True)
db = typer.Typer(add_help_option=True, no_args_is_help=True)
dev_db = typer.Typer(add_help_option=True, no_args_is_help=True)
cli.add_typer(dev, name="dev")
cli.add_typer(db, name="db")
dev.add_typer(dev_db, name="db")


API = "project_manager.api:api"
COMPOSE_FILE = Path(__file__).parents[2] / "compose.yaml"


def run_compose():
    subprocess.run(
        ["docker", "compose", "up", "-d"], check=False, cwd=COMPOSE_FILE.parent
    )


def dev_environment():
    compose_data = yaml.load(COMPOSE_FILE.read_text(), yaml.SafeLoader)
    os.environ["PGPASSWORD"] = compose_data["services"]["db"]["environment"][
        "POSTGRES_PASSWORD"
    ]
    os.environ["PGDATABASE"] = compose_data["services"]["db"]["environment"][
        "POSTGRES_DB"
    ]
    os.environ["PGUSER"] = compose_data["services"]["db"]["environment"][
        "POSTGRES_USER"
    ]
    os.environ["PGHOST"] = "127.0.0.1"
    os.environ["PGPORT"] = "5432"


@contextmanager
def testcontainer_postgresql():
    with PostgresContainer() as pg:
        os.environ["PGPASSWORD"] = pg.password
        os.environ["PGDATABASE"] = pg.dbname
        os.environ["PGUSER"] = pg.username
        os.environ["PGHOST"] = "127.0.0.1"
        os.environ["PGPORT"] = str(pg.get_exposed_port(pg.port))
        yield


@cli.command(name="api")
def api(workers: Annotated[int, typer.Option(envvar="API_WORKERS")]):
    """Run api"""

    uvicorn.run("project_manager.api:api", workers=workers)


@dev.command("api")
def dev_api():
    """Run development api woth hot reload."""
    dev_environment()
    with ThreadPoolExecutor() as executor:
        executor.submit(run_compose)
        uvicorn.run("project_manager.api:api", reload=True)


def _db_upgrade(revision: str):
    return Database().downgrade(revision=revision)


def _db_downgrade(revision: str):
    return Database().downgrade(revision=revision)


def _db_stamp(revision: str):
    return Database().stamp(revision=revision)


@db.command("upgrade")
def upgrade(revision: Annotated[str | None, typer.Option(envvar="DB_REVISION")] = None):
    _db_upgrade(revision=revision or "head")


@db.command("upgrade")
def downgrade(revision: Annotated[str | None, typer.Option()] = None):
    _db_downgrade(revision=revision or "-1")


@db.command("stamp")
def stamp(revision: Annotated[str | None, typer.Option()] = None):
    _db_stamp(revision=revision or "head")


@dev_db.command("upgrade")
def dev_upgrade(
    revision: Annotated[str | None, typer.Option(envvar="DB_REVISION")] = None,
):
    _db_upgrade(revision=revision or "head")


@dev_db.command("upgrade")
def dev_downgrade(revision: Annotated[str | None, typer.Option()] = None):
    _db_downgrade(revision=revision or "-1")


@dev_db.command("stamp")
def dev_stamp(revision: Annotated[str | None, typer.Option()] = None):
    _db_stamp(revision=revision or "head")


@dev_db.command("revision")
def dev_revision(
    message: Annotated[str, typer.Option()],
    autogenerate: Annotated[bool, typer.Option()] = True,
):
    with testcontainer_postgresql():
        _db_upgrade("head")
        return Database().create_revision(message=message, autogenerate=autogenerate)
