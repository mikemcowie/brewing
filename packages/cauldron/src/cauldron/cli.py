from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
import uvicorn

from cauldron.db import Database, PostgresqlSettings
from cauldron.development import (
    DevelopmentEnvironment,
)
from cauldron.logging import get_logger, setup_logging

if TYPE_CHECKING:
    from collections.abc import Callable

    from cauldron.http import CauldronHTTP


def asgi_application_sting(factory: Callable[[], CauldronHTTP], /):
    return f"{factory.__module__}:{factory.__name__}"


def build_cli(  # noqa: C901, PLR0915
    api_factory: Callable[[], CauldronHTTP], dev_api_factory: Callable[[], CauldronHTTP]
):
    setup_logging()
    logger = get_logger()
    cli = typer.Typer(add_help_option=True, no_args_is_help=True)
    dev = typer.Typer(add_help_option=True, no_args_is_help=True)
    db = typer.Typer(add_help_option=True, no_args_is_help=True)
    dev_db = typer.Typer(add_help_option=True, no_args_is_help=True)
    cli.add_typer(dev, name="dev")
    cli.add_typer(db, name="db")
    dev.add_typer(dev_db, name="db")
    development_environment = DevelopmentEnvironment()

    @cli.command(name="api")
    def api(workers: Annotated[int, typer.Option(envvar="API_WORKERS")]) -> None:
        """Run api"""
        logger.info("starting API")
        uvicorn.run(asgi_application_sting(api_factory), workers=workers, factory=True)
        logger.info("shut down API")

    @dev.command("api")
    def dev_api() -> None:
        """Run development api woth hot reload."""
        development_environment.run()
        logger.info("starting dev API")
        uvicorn.run(asgi_application_sting(dev_api_factory), reload=True, factory=True)
        logger.info("shut down dev API")

    def _db_upgrade(revision: str) -> None:
        logger.info("upgrading database", revision=revision)
        Database[PostgresqlSettings]().upgrade(revision=revision)
        logger.info("finished upgrading database", revision=revision)

    def _db_downgrade(revision: str) -> None:
        logger.info("downgrading database", revision=revision)
        Database[PostgresqlSettings]().downgrade(revision=revision)
        logger.info("finished downgrading database", revision=revision)

    def _db_stamp(revision: str) -> None:
        logger.info("stamping database", revision=revision)
        Database[PostgresqlSettings]().stamp(revision=revision)
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
        development_environment.run()
        _db_upgrade(revision=revision or "head")

    @dev_db.command("downgrade")
    def dev_downgrade(revision: Annotated[str | None, typer.Option()] = None) -> None:
        development_environment.run()
        _db_downgrade(revision=revision or "-1")

    @dev_db.command("stamp")
    def dev_stamp(revision: Annotated[str | None, typer.Option()] = None) -> None:
        development_environment.run()
        _db_stamp(revision=revision or "head")

    @dev_db.command("revision")
    def dev_revision(
        message: Annotated[str, typer.Option()],
        autogenerate: Annotated[bool, typer.Option()] = True,
    ) -> None:
        with development_environment.testcontainer_postgresql():
            _db_upgrade("head")
            return Database[PostgresqlSettings]().create_revision(
                message=message, autogenerate=autogenerate
            )

    return cli
