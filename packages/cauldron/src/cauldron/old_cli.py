from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer
import uvicorn

from cauldron.cli import CLI
from cauldron.development import (
    DevelopmentEnvironment,
)
from cauldron.logging import get_logger, setup_logging

if TYPE_CHECKING:
    from collections.abc import Callable

    from cauldron.db.database import Migrations, MigrationsProtocol
    from cauldron.db.settings import PostgresqlSettings
    from cauldron.http import CauldronHTTP


logger = get_logger()


def asgi_application_sting(factory: Callable[[], CauldronHTTP], /):
    return f"{factory.__module__}:{factory.__name__}"


class DatabaseCLI[MigrationsT: MigrationsProtocol](CLI):
    def __init__(
        self,
        name: str,
        /,
        *children: CLI,
        migrations: MigrationsT,
        typer: typer.Typer | None = None,
    ):
        self._migrations = migrations
        super().__init__(name, *children, typer=typer)

    def _db_upgrade(self, revision: str) -> None:
        logger.info("upgrading database", revision=revision)
        self._migrations.upgrade(revision=revision)
        logger.info("finished upgrading database", revision=revision)

    def _db_downgrade(self, revision: str) -> None:
        logger.info("downgrading database", revision=revision)
        self._migrations.downgrade(revision=revision)
        logger.info("finished downgrading database", revision=revision)

    def _db_stamp(self, revision: str) -> None:
        logger.info("stamping database", revision=revision)
        self._migrations.stamp(revision=revision)
        logger.info("finished stamping database", revision=revision)

    def upgrade(
        self,
        revision: Annotated[str | None, typer.Option(envvar="DB_REVISION")] = None,
    ) -> None:
        self._db_upgrade(revision=revision or "head")

    def downgrade(self, revision: Annotated[str | None, typer.Option()] = None) -> None:
        self._db_downgrade(revision=revision or "-1")

    def stamp(self, revision: Annotated[str | None, typer.Option()] = None) -> None:
        self._db_stamp(revision=revision or "head")


class DevDatabaseCLI[MigrationsT: MigrationsProtocol](DatabaseCLI[MigrationsT]):
    def __init__(
        self,
        name: str,
        /,
        *children: CLI,
        migrations: MigrationsT,
        typer: typer.Typer | None = None,
    ):
        super().__init__(name, *children, migrations=migrations, typer=typer)
        self._dev = DevelopmentEnvironment()
        self._dev.run()

    def revision(
        self,
        message: Annotated[str, typer.Option()],
        autogenerate: Annotated[bool, typer.Option()] = True,
    ) -> None:
        with self._dev.testcontainer_postgresql():
            self._db_upgrade("head")
            return self._migrations.create_revision(
                message=message, autogenerate=autogenerate
            )


class AppCLI(CLI):
    def __init__(
        self,
        name: str,
        /,
        *children: CLI,
        api_factory: Callable[[], CauldronHTTP],
        typer: typer.Typer | None = None,
    ):
        self._api_factory = api_factory
        super().__init__(name, *children, typer=typer)

    def api(self, workers: Annotated[int, typer.Option(envvar="API_WORKERS")]) -> None:
        """Run api"""
        logger.info("starting API")
        uvicorn.run(
            asgi_application_sting(self._api_factory), workers=workers, factory=True
        )
        logger.info("shut down API")


class DevAppCLI(CLI):
    def __init__(
        self,
        name: str,
        /,
        *children: CLI,
        api_factory: Callable[[], CauldronHTTP],
        typer: typer.Typer | None = None,
    ):
        self._api_factory = api_factory
        super().__init__(name, *children, typer=typer)

    def api(self) -> None:
        """Run development api with hot reload."""
        DevelopmentEnvironment().run()
        logger.info("starting dev API")
        uvicorn.run(
            asgi_application_sting(self._api_factory), reload=True, factory=True
        )
        logger.info("shut down dev API")


def build_cli(
    api_factory: Callable[[], CauldronHTTP],
    dev_api_factory: Callable[[], CauldronHTTP],
    migrations: Migrations[PostgresqlSettings],
):
    setup_logging()
    cli = AppCLI(
        "app",
        DatabaseCLI("db", migrations=migrations),
        DevAppCLI(
            "dev",
            DevDatabaseCLI("db", migrations=migrations),
            api_factory=dev_api_factory,
        ),
        api_factory=api_factory,
    )
    return cli.typer
