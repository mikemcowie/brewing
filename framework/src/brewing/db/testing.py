"""Database testing utilities."""

from __future__ import annotations

import asyncio
import os

import tempfile
from collections.abc import Callable, Generator, MutableMapping
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from brewing.db.settings import DatabaseType
from testcontainers.mysql import MySqlContainer
from testcontainers.postgres import PostgresContainer

if TYPE_CHECKING:
    from brewing.db.types import DatabaseProtocol


@contextmanager
def env(
    new_env: dict[str, str], environ: MutableMapping[str, str] = os.environ
) -> Generator[None]:
    """Temporarily modify environment (or other provided mapping), restore original values on cleanup."""
    orig: dict[str, str | None] = {}
    for key, value in new_env.items():
        orig[key] = environ.get(key)
        environ[key] = value
    yield
    # Cleanup - restore the original values
    # or delete if they weren't set.
    for key, value in orig.items():
        if value is None:
            del environ[key]
        else:
            environ[key] = value


type TestingDatabase = Callable[[], AbstractContextManager[None]]


@contextmanager
def _postgresql():
    with (
        PostgresContainer() as pg,
        env(
            {
                "PGHOST": "127.0.0.1",
                "PGPORT": str(pg.get_exposed_port(pg.port)),
                "PGDATABASE": pg.dbname,
                "PGUSER": pg.username,
                "PGPASSWORD": pg.password,
            }
        ),
    ):
        yield


@contextmanager
def _sqlite():
    with (
        tempfile.TemporaryDirectory() as db_dir,
        env({"SQLITE_DATABASE": str(Path(db_dir) / "db.sqlite")}),
    ):
        yield


@contextmanager
def _mysql(image: str = "mysql:latest"):
    with (
        MySqlContainer(image=image) as mysql,
        env(
            {
                "MYSQL_HOST": "127.0.0.1",
                "MYSQL_USER": mysql.username,
                "MYSQL_PWD": mysql.password,
                "MYSQL_TCP_PORT": str(mysql.get_exposed_port(mysql.port)),
                "MYSQL_DATABASE": mysql.dbname,
            }
        ),
    ):
        yield


mariadb = partial(_mysql, image="mariadb:latest")


_TEST_DATABASE_IMPLEMENTATIONS: dict[DatabaseType, TestingDatabase] = {
    DatabaseType.sqlite: _sqlite,
    DatabaseType.postgresql: _postgresql,
    DatabaseType.mysql: _mysql,
    DatabaseType.mariadb: mariadb,
}


@contextmanager
def testing(db_type: DatabaseType):
    """Temporarily create and set environment variables for connection to given db type."""
    with _TEST_DATABASE_IMPLEMENTATIONS[db_type]():
        yield


@asynccontextmanager
async def upgraded(db: DatabaseProtocol):
    """Temporarily deploys tables for given database, dropping them in cleanup phase."""
    async with db.engine.begin() as conn:
        for metadata in db.metadata:
            await conn.run_sync(metadata.create_all)
            asyncio.get_running_loop().run_in_executor(
                None, db.migrations.stamp, "head"
            )

    yield
    async with db.engine.begin() as conn:
        for metadata in db.metadata:
            await conn.run_sync(metadata.drop_all)


# make sure pytest doesn't try this
testing.__test__ = False  # type: ignore
