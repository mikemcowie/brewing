from __future__ import annotations

from typing import Annotated

import typer
import uvicorn
from cauldron.db import Database
from cauldron.logging import get_logger, setup_logging
from cauldron.testing import (
    dev_environment,
    testcontainer_postgresql,
)

setup_logging()
logger = get_logger()
cli = typer.Typer(add_help_option=True, no_args_is_help=True)
dev = typer.Typer(add_help_option=True, no_args_is_help=True)
db = typer.Typer(add_help_option=True, no_args_is_help=True)
dev_db = typer.Typer(add_help_option=True, no_args_is_help=True)
cli.add_typer(dev, name="dev")
cli.add_typer(db, name="db")
dev.add_typer(dev_db, name="db")


API = "project_manager.api:api"
DEV_API = "project_manager.api:dev_api"


@cli.command(name="api")
def api(workers: Annotated[int, typer.Option(envvar="API_WORKERS")]) -> None:
    """Run api"""
    logger.info("starting API")
    uvicorn.run(API, workers=workers, factory=True)
    logger.info("shut down API")


@dev.command("api")
def dev_api() -> None:
    """Run development api woth hot reload."""
    dev_environment()
    logger.info("starting dev API")
    uvicorn.run(DEV_API, reload=True, factory=True)
    logger.info("shut down dev API")


def _db_upgrade(revision: str) -> None:
    logger.info("upgrading database", revision=revision)
    Database().upgrade(revision=revision)
    logger.info("finished upgrading database", revision=revision)


def _db_downgrade(revision: str) -> None:
    logger.info("downgrading database", revision=revision)
    Database().downgrade(revision=revision)
    logger.info("finished downgrading database", revision=revision)


def _db_stamp(revision: str) -> None:
    logger.info("stamping database", revision=revision)
    Database().stamp(revision=revision)
    logger.info("finished stamping database", revision=revision)


@db.command("upgrade")
def upgrade(
    revision: Annotated[str | None, typer.Option(envvar="DB_REVISION")] = None,
) -> None:
    _db_upgrade(revision=revision or "head")


@db.command("downgrade")
def downgrade(revision: Annotated[str | None, typer.Option()] = None) -> None:
    _db_downgrade(revision=revision or "-1")


@db.command("stamp")
def stamp(revision: Annotated[str | None, typer.Option()] = None) -> None:
    _db_stamp(revision=revision or "head")


@dev_db.command("upgrade")
def dev_upgrade(
    revision: Annotated[str | None, typer.Option(envvar="DB_REVISION")] = None,
) -> None:
    dev_environment()
    _db_upgrade(revision=revision or "head")


@dev_db.command("downgrade")
def dev_downgrade(revision: Annotated[str | None, typer.Option()] = None) -> None:
    dev_environment()
    _db_downgrade(revision=revision or "-1")


@dev_db.command("stamp")
def dev_stamp(revision: Annotated[str | None, typer.Option()] = None) -> None:
    dev_environment()
    _db_stamp(revision=revision or "head")


@dev_db.command("revision")
def dev_revision(
    message: Annotated[str, typer.Option()],
    autogenerate: Annotated[bool, typer.Option()] = True,
) -> None:
    with testcontainer_postgresql():
        _db_upgrade("head")
        return Database().create_revision(message=message, autogenerate=autogenerate)
